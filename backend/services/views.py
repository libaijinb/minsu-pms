from datetime import timedelta

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from listings.models import Calendar
from users.models import User
from users.permissions import IsCleaner, IsOperator, IsRepairer
from .models import CleaningTask, RepairTicket
from .serializers import (CleaningDispatchSerializer, CleaningFinishSerializer,
                          CleaningTaskSerializer, RepairCreateSerializer,
                          RepairDispatchSerializer, RepairHandleSerializer,
                          RepairTicketSerializer)


class CleaningTaskViewSet(viewsets.ModelViewSet):
    """
    清洁任务：
    - 运营看全部、房东看自己房源的、保洁看派给自己的
    - 派工冲突由 (cleaner, task_date, slot) 唯一约束拦截（BR-CLN-03）
    """

    serializer_class = CleaningTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CleaningTask.objects.select_related('listing', 'cleaner')
        if user.is_superuser or user.roles.filter(code='operator').exists():
            return qs.all()
        if user.roles.filter(code='landlord').exists():
            return qs.filter(listing__owner=user)
        return qs.filter(cleaner=user)  # 保洁只看自己的

    def get_permissions(self):
        if self.action in ('assign', 'review', 'create'):
            return [IsOperator()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """运营派工：指定保洁 + 日期 + 时段，冲突返回 409（BR-CLN-03）。
        注意：action 名不能叫 dispatch——会覆盖 APIView.dispatch 框架方法！"""
        task = self.get_object()
        serializer = CleaningDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cleaner = User.objects.filter(pk=data['cleaner'], roles__code='cleaner').first()
        if not cleaner:
            return Response({'detail': '指定的用户不是保洁角色'}, status=status.HTTP_400_BAD_REQUEST)
        task.cleaner = cleaner
        task.task_date = data['task_date']
        task.slot = data['slot']
        try:
            task.save()  # 撞唯一约束会抛 IntegrityError
        except IntegrityError:
            return Response({'detail': '该保洁在此日期时段已有任务，请换时段或换人'},
                            status=status.HTTP_409_CONFLICT)
        task.status = 'assigned'
        task.assigned_at = timezone.now()
        task.save(update_fields=['status', 'assigned_at'])
        return Response(CleaningTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        """保洁标记完成：上传照片，状态转待复核（BR-CLN-05）"""
        task = self.get_object()
        serializer = CleaningFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if task.status != 'assigned':
            return Response({'detail': '仅已派工任务可提交完成'}, status=status.HTTP_400_BAD_REQUEST)
        task.photos = serializer.validated_data['photos']
        task.status = 'reviewing'
        task.finished_at = timezone.now()
        task.save(update_fields=['photos', 'status', 'finished_at'])
        return Response(CleaningTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """运营复核：通过则任务完成"""
        task = self.get_object()
        if task.status != 'reviewing':
            return Response({'detail': '仅待复核任务可复核'}, status=status.HTTP_400_BAD_REQUEST)
        task.status = 'done'
        task.reviewed_at = timezone.now()
        task.save(update_fields=['status', 'reviewed_at'])
        return Response(CleaningTaskSerializer(task).data)


class RepairTicketViewSet(viewsets.ModelViewSet):
    """
    维修工单：
    - 运营看全部、房东看自己房源的、维修看派给自己的、客人看自己订单报修的
    - 派工紧急工单自动锁定房源当天+明天日历（BR-REP-03），验收后解锁
    """

    serializer_class = RepairTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = RepairTicket.objects.select_related('listing', 'repairer')
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or user.roles.filter(code='operator').exists():
            return qs.all()
        if user.roles.filter(code='landlord').exists():
            return qs.filter(listing__owner=user)
        if user.roles.filter(code='repairer').exists():
            return qs.filter(repairer=user)
        return qs.filter(order__guest=user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]  # 客人/房东/运营均可报修（serializer 校验客人归属）
        if self.action in ('assign', 'close'):
            return [IsOperator()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return RepairCreateSerializer
        if self.action == 'dispatch':
            return RepairDispatchSerializer
        if self.action == 'handle':
            return RepairHandleSerializer
        return RepairTicketSerializer

    def perform_create(self, serializer):
        user = self.request.user
        source = 'guest' if user.roles.filter(code='guest').exists() else \
                 'landlord' if user.roles.filter(code='landlord').exists() else 'operator'
        serializer.save(source=source)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """运营派工：紧急工单自动锁定房源当天+明天（BR-REP-03）"""
        ticket = self.get_object()
        serializer = RepairDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repairer = User.objects.filter(pk=serializer.validated_data['repairer'],
                                       roles__code='repairer').first()
        if not repairer:
            return Response({'detail': '指定的用户不是维修角色'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.repairer = repairer
        ticket.status = 'assigned'
        ticket.save(update_fields=['repairer', 'status'])
        if ticket.urgency == 'urgent':
            today = timezone.localdate()
            Calendar.objects.filter(
                listing=ticket.listing, date__range=[today, today + timedelta(days=1)],
                status__in=['available', 'locked']).update(
                status='locked', lock_reason=f'紧急维修：{ticket.title}')
        return Response(RepairTicketSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def handle(self, request, pk=None):
        """维修提交处理结果：记录费用，状态转待验收"""
        ticket = self.get_object()
        serializer = RepairHandleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if ticket.status != 'assigned':
            return Response({'detail': '仅已派工工单可提交处理'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.cost = serializer.validated_data['cost']
        ticket.desc += f'\n[维修记录] {serializer.validated_data.get("note", "")}'.rstrip()
        ticket.status = 'accepting'
        ticket.save(update_fields=['cost', 'desc', 'status'])
        return Response(RepairTicketSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """运营验收关单：完工解锁被锁定的日期"""
        ticket = self.get_object()
        if ticket.status != 'accepting':
            return Response({'detail': '仅待验收工单可关单'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = 'done'
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=['status', 'closed_at'])
        Calendar.objects.filter(
            listing=ticket.listing, status='locked',
            lock_reason=f'紧急维修：{ticket.title}').update(status='available', lock_reason='')
        return Response(RepairTicketSerializer(ticket).data)
