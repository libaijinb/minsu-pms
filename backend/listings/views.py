from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from orders.models import BookingOrder
from .models import Calendar, Listing, PriceRule
from users.permissions import IsLandlordOrOperator, IsOperator
from .serializers import CalendarSerializer, ListingSerializer, PriceRuleSerializer
from .services import ensure_calendar


class ListingViewSet(viewsets.ModelViewSet):
    """
    房源管理：
    - 浏览（list/retrieve）对游客开放，只返回已上架房源（商业网站惯例）
    - 房东看自己的、运营看全部的（数据范围隔离）
    - 状态流转走专用 action：submit/audit/online/offline
    """

    serializer_class = ListingSerializer
    permission_classes = [AllowAny]  # 浏览开放；写操作在各 action 内单独收紧
    filterset_fields = ['type', 'city', 'district']
    ordering_fields = ['rating', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Listing.objects.select_related('owner')
        action_name = self.action
        # calendar 是读操作：订房页面游客/客人必须能看，与 list/retrieve 同路处理
        if action_name in ('list', 'retrieve', 'calendar'):
            if user.is_authenticated:
                if user.is_superuser or user.roles.filter(code='operator').exists():
                    return qs.all().order_by('-created_at')
                if user.roles.filter(code='landlord').exists():
                    # 房东：自己的房源（含下架）+ 平台上架房源
                    return qs.filter(Q(owner=user) | Q(status='online')).order_by('-created_at')
            return qs.filter(status='online').order_by('-rating', '-created_at')
        # 写操作：房东只能动自己的，运营可动全部
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or user.roles.filter(code='operator').exists():
            return qs.all()
        return qs.filter(owner=user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsLandlordOrOperator()]
        if self.action in ('update', 'partial_update', 'destroy', 'submit', 'online', 'offline',
                           'batch_price', 'close_dates', 'open_dates'):
            return [IsAuthenticated()]  # 对象级归属在校验/queryset 里把关
        if self.action == 'audit':
            return [IsOperator()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, status='draft')

    # ---------- 状态流转 ----------

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """房东提交审核：草稿 -> 审核中（BR-LST-01）"""
        listing = self.get_object()
        if listing.status != 'draft':
            return Response({'detail': '仅草稿状态可提交审核'}, status=status.HTTP_400_BAD_REQUEST)
        listing.status = 'pending'
        listing.save(update_fields=['status'])
        return Response({'detail': '已提交审核'})

    @action(detail=True, methods=['post'])
    def audit(self, request, pk=None):
        """运营审核：通过 -> 已上架（并生成日历）；驳回 -> 草稿（BR-LST-01）"""
        listing = self.get_object()
        passed = request.data.get('passed', True)
        reason = request.data.get('reason', '')
        if listing.status != 'pending':
            return Response({'detail': '仅审核中状态可审核'}, status=status.HTTP_400_BAD_REQUEST)
        if passed:
            listing.status = 'online'
            listing.save(update_fields=['status'])
            ensure_calendar(listing)  # 上架即铺未来 365 天日历（FR-CAL-01）
            return Response({'detail': '审核通过，房源已上架'})
        listing.status = 'draft'
        listing.save(update_fields=['status'])
        return Response({'detail': f'已驳回：{reason}'})

    @action(detail=True, methods=['post'])
    def online(self, request, pk=None):
        """上架"""
        listing = self.get_object()
        if listing.status not in ('draft', 'offline'):
            return Response({'detail': '当前状态不可上架'}, status=status.HTTP_400_BAD_REQUEST)
        listing.status = 'online'
        listing.save(update_fields=['status'])
        ensure_calendar(listing)
        return Response({'detail': '已上架'})

    @action(detail=True, methods=['post'])
    def offline(self, request, pk=None):
        """下架：存在未来有效订单的房源不允许下架（BR-LST-03）"""
        listing = self.get_object()
        if listing.status != 'online':
            return Response({'detail': '仅已上架状态可下架'}, status=status.HTTP_400_BAD_REQUEST)
        future_orders = BookingOrder.objects.filter(
            listing=listing, checkin_date__gte=timezone.localdate(),
            status__in=['pending_pay', 'pending_confirm', 'confirmed']).exists()
        if future_orders:
            return Response({'detail': '该房源还有未入住的订单，不能下架'},
                            status=status.HTTP_400_BAD_REQUEST)
        listing.status = 'offline'
        listing.save(update_fields=['status'])
        return Response({'detail': '已下架'})

    # ---------- 日历操作 ----------

    @action(detail=True, methods=['get'])
    def calendar(self, request, pk=None):
        """月份日历查询：默认返回本月，支持 ?start=&end=（FR-CAL-02）"""
        listing = self.get_object()
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if not start:
            today = timezone.localdate()
            start = today.replace(day=1)
            end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        rows = Calendar.objects.filter(listing=listing, date__range=[start, end]).order_by('date')
        return Response(CalendarSerializer(rows, many=True).data)

    @action(detail=True, methods=['post'], url_path='batch-price')
    def batch_price(self, request, pk=None):
        """区间批量改价：只改可订晚，已订/锁定晚跳过（BR-CAL-08）"""
        listing = self.get_object()
        start = request.data.get('start')
        end = request.data.get('end')
        price = request.data.get('price')
        if not (start and end and price):
            return Response({'detail': '请提供 start/end/price'}, status=status.HTTP_400_BAD_REQUEST)
        updated = (Calendar.objects
                   .filter(listing=listing, date__range=[start, end], status='available')
                   .update(price=price))
        return Response({'detail': f'已更新 {updated} 个可订晚的价格'})

    @action(detail=True, methods=['post'], url_path='close-dates')
    def close_dates(self, request, pk=None):
        """关闭日期：自留/停售，已订晚不可关"""
        listing = self.get_object()
        dates = request.data.get('dates', [])
        reason = request.data.get('reason', '房东关闭')
        if not dates:
            return Response({'detail': '请提供 dates 列表'}, status=status.HTTP_400_BAD_REQUEST)
        booked = Calendar.objects.filter(listing=listing, date__in=dates, status='booked').count()
        if booked:
            return Response({'detail': f'所选日期有 {booked} 个晚已被预订，不能关闭'},
                            status=status.HTTP_400_BAD_REQUEST)
        Calendar.objects.filter(listing=listing, date__in=dates).update(status='closed', lock_reason=reason)
        return Response({'detail': '已关闭'})

    @action(detail=True, methods=['post'], url_path='open-dates')
    def open_dates(self, request, pk=None):
        """重新打开已关闭/锁定的日期为可订"""
        listing = self.get_object()
        dates = request.data.get('dates', [])
        if not dates:
            return Response({'detail': '请提供 dates 列表'}, status=status.HTTP_400_BAD_REQUEST)
        Calendar.objects.filter(listing=listing, date__in=dates,
                                status__in=['closed', 'locked']).update(status='available', lock_reason='')
        return Response({'detail': '已打开'})


class PriceRuleViewSet(viewsets.ModelViewSet):
    """价格规则 CRUD：房东管理自己房源的规则，运营可管理全部"""

    serializer_class = PriceRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = PriceRule.objects.select_related('listing')
        if user.is_superuser or user.roles.filter(code='operator').exists():
            return qs.all()
        return qs.filter(listing__owner=user)

    def perform_create(self, serializer):
        listing = serializer.validated_data['listing']
        if listing.owner != self.request.user and not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('不能给他人房源配置规则')
        serializer.save()
