from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Listing
from users.permissions import IsLandlordOrOperator, IsOperator
from . import services
from .models import BookingOrder, CheckinRecord, DepositDeduction, InspectionRecord
from .serializers import (CancelSerializer, CheckinCreateSerializer, OrderCreateSerializer,
                          OrderDetailSerializer, OrderSerializer, InspectionSerializer)
from services.models import RepairTicket


class OrderViewSet(viewsets.GenericViewSet):
    """
    订单接口：只提供创建/列表/详情 + 状态机动作（pay/confirm/cancel/checkin/checkout/noshow）。
    订单不可编辑、不可删除——一切变更必须走状态机留痕（BR-ORD-07）。
    """

    queryset = BookingOrder.objects.select_related('listing', 'guest').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'retrieve':
            return OrderDetailSerializer
        if self.action == 'cancel':
            return CancelSerializer
        if self.action == 'checkin':
            return CheckinCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser or user.roles.filter(code='operator').exists():
            return qs
        if user.roles.filter(code='landlord').exists():
            return qs.filter(listing__owner=user)
        return qs.filter(guest=user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]  # 客人下单
        if self.action in ('confirm', 'cancel'):
            return [IsLandlordOrOperator()]  # 房东/运营确认与取消
        if self.action in ('checkin', 'checkout', 'noshow'):
            return [IsOperator()]  # 入住退房是运营动作
        if self.action == 'pay':
            return [IsAuthenticated()]  # 下单本人支付（queryset 已限制）
        return [IsAuthenticated()]

    def list(self, request):
        """订单列表：支持 status/listing/channel 筛选"""
        qs = self.get_queryset()
        status_param = request.query_params.get('status')
        listing_id = request.query_params.get('listing')
        channel = request.query_params.get('channel')
        if status_param:
            qs = qs.filter(status=status_param)
        if listing_id:
            qs = qs.filter(listing_id=listing_id)
        if channel:
            qs = qs.filter(channel=channel)
        page = self.paginate_queryset(qs.order_by('-created_at'))
        serializer = OrderSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        return Response(OrderDetailSerializer(order).data)

    def create(self, request):
        """创建订单：占房与建订单同事务（services.create_order）"""
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            order = services.create_order(
                guest=request.user, listing=data['listing'],
                checkin_date=data['checkin_date'], checkout_date=data['checkout_date'],
                guests_count=data['guests_count'], channel=data['channel'])
        except services.CalendarConflict as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

    # ---------- 状态机动作 ----------

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """模拟支付：真实环境由支付宝异步回调驱动，这里直接成功"""
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        if order.guest != request.user and not request.user.is_superuser:
            return Response({'detail': '只能支付本人的订单'}, status=status.HTTP_403_FORBIDDEN)
        try:
            services.pay_order(order)
        except services.InvalidTransition as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """房东/运营确认订单"""
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        try:
            services.transition(order, 'confirm', operator=request.user, remark='房东确认订单')
        except services.InvalidTransition as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消订单：按政策计算退款并释放日历"""
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = services.cancel_order(order, request.user, serializer.validated_data['reason'])
        except services.InvalidTransition as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': f'已取消，应退 ¥{refund}', 'refund_amount': refund})

    @action(detail=True, methods=['post'])
    def checkin(self, request, pk=None):
        """入住登记：实名信息 + 押金（BR-CIO-01/02）"""
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        serializer = CheckinCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        deposit = data.get('deposit_amount') or order.listing.deposit_amount
        try:
            services.do_checkin(order, request.user, data['guest_names'],
                                data['id_card'], data['phone'], deposit)
        except services.InvalidTransition as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        """退房：转状态 + 自动生成清洁任务（幂等）+ 记录退房时间（BR-CIO-02）"""
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        try:
            services.do_checkout(order, request.user)
        except services.InvalidTransition as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'])
    def noshow(self, request, pk=None):
        """标记未入住：全扣款 + 释放日历（BR-ORD-04 极端分支）"""
        order = get_object_or_404(self.get_queryset(), order_no=pk)
        try:
            services.transition(order, 'noshow', operator=request.user, remark='客人未入住')
        except services.InvalidTransition as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        order.refund_amount = 0
        order.save(update_fields=['refund_amount'])
        services.release_calendar(order.listing, order.checkin_date, order.checkout_date)
        return Response({'detail': '已标记未入住，房费全扣'})


class InspectionListView(APIView):
    """
    查房任务列表（运营视角）：
    - ?status=todo  待查房：已退房且无查房记录的订单
    - ?status=done  已查房：返回查房记录
    查房任务不建表，用查询表达——少一张表，逻辑一样（需求分析 4.7 的落地选择）。
    """

    permission_classes = [IsOperator]

    def get(self, request):
        if request.query_params.get('status') == 'todo':
            orders = (BookingOrder.objects
                      .filter(status='checked_out', inspection__isnull=True)
                      .select_related('listing', 'guest')
                      .order_by('-updated_at'))
            data = [{'order_no': o.order_no, 'listing_title': o.listing.title,
                     'guest_name': o.guest.first_name, 'checkout_date': o.checkout_date,
                     'has_deposit': o.checkin.deposit_amount if o.checkin else 0,
                     'deposit_status': o.checkin.deposit_status if o.checkin else ''}
                    for o in orders]
            return Response(data)
        records = (InspectionRecord.objects
                   .select_related('order__listing', 'inspector')
                   .order_by('-created_at')[:50])
        return Response(InspectionSerializer(records, many=True).data)


class InspectionSubmitView(APIView):
    """运营提交查房结果：写查房记录 + 定损生成押金扣减 + 损坏项自动建维修工单（BR-INS/REP-02）"""

    permission_classes = [IsOperator]

    def post(self, request):
        order_no = request.data.get('order_no')
        items = request.data.get('items', [])
        order = get_object_or_404(BookingOrder, order_no=order_no)
        if order.status != 'checked_out':
            return Response({'detail': '仅已退房订单可查房'}, status=status.HTTP_400_BAD_REQUEST)
        if InspectionRecord.objects.filter(order=order).exists():
            return Response({'detail': '该订单已查房'}, status=status.HTTP_400_BAD_REQUEST)
        damage_total = sum(float(i.get('amount', 0)) for i in items if i.get('result') == 'damage')
        conclusion = 'fail' if damage_total > 0 else 'pass'
        inspection = InspectionRecord.objects.create(
            order=order, items=items, damage_total=damage_total,
            conclusion=conclusion, inspector=request.user)
        # 定损逐条：押金扣减 + 自动生成维修工单
        for item in items:
            if item.get('result') != 'damage':
                continue
            ticket = RepairTicket.objects.create(
                listing=order.listing, order=order, source='inspection',
                title=item.get('name', '损坏项维修'), desc=item.get('note', ''),
                cost=item.get('amount', 0), status='pending')
            DepositDeduction.objects.create(
                inspection=inspection, item=item.get('name', ''),
                amount=item.get('amount', 0), repair_ticket=ticket, status='confirmed')
        # 押金状态更新：扣减后剩余退还（前端/运营据此操作，这里只更新状态标记）
        if order.checkin and damage_total > 0:
            order.checkin.deposit_status = 'deducted'
            order.checkin.save(update_fields=['deposit_status'])
        elif order.checkin:
            order.checkin.deposit_status = 'refunded'
            order.checkin.save(update_fields=['deposit_status'])
        return Response(InspectionSerializer(inspection).data, status=status.HTTP_201_CREATED)
