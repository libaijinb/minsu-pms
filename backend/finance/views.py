from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsFinance, IsOperator
from . import services
from .models import PayoutRecord, Settlement
from .serializers import PayoutRecordSerializer, SettlementDetailSerializer, SettlementSerializer


class SettlementViewSet(viewsets.ModelViewSet):
    """
    结算单：
    - 房东看自己的、财务/运营看全部
    - payout 动作由财务执行；run 动作手动触发某周期月结（演示/补跑用）
    """

    queryset = Settlement.objects.select_related('landlord').all()
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']  # 结算单不可改不可删，只读 + 动作

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SettlementDetailSerializer
        return SettlementSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser or user.roles.filter(code__in=['operator', 'finance']).exists():
            return qs
        return qs.filter(landlord=user)

    def get_permissions(self):
        if self.action == 'payout':
            return [IsFinance()]
        if self.action == 'run':
            return [IsOperator()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def payout(self, request, pk=None):
        """财务执行分账：?success=false 可模拟失败用于演示重试"""
        settlement = self.get_object()
        if settlement.status == 'paid':
            return Response({'detail': '该结算单已分账'}, status=status.HTTP_400_BAD_REQUEST)
        success = request.query_params.get('success', 'true') != 'false'
        payout = services.run_payout(settlement, success=success)
        if not payout:
            return Response({'detail': '没有待分账记录'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PayoutRecordSerializer(payout).data)

    @action(detail=False, methods=['post'])
    def run(self, request):
        """手动触发月结：指定房东 id 与周期（默认上月），演示/补跑用"""
        landlord_id = request.data.get('landlord')
        period = request.data.get('period') or services.last_period()
        from django.contrib.auth import get_user_model
        landlord = get_user_model().objects.filter(pk=landlord_id).first()
        if not landlord:
            return Response({'detail': '房东不存在'}, status=status.HTTP_400_BAD_REQUEST)
        settlement, created = services.settle_period(landlord, period)
        if not settlement:
            return Response({'detail': f'{period} 没有可结算的订单'})
        return Response(SettlementSerializer(settlement).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PayoutRetryView(viewsets.GenericViewSet):
    """分账重试：财务对失败记录重新执行"""

    permission_classes = [IsFinance]
    queryset = PayoutRecord.objects.all()
    serializer_class = PayoutRecordSerializer

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        payout = self.get_object()
        if payout.status != 'failed':
            return Response({'detail': '仅失败的分账记录可重试'}, status=status.HTTP_400_BAD_REQUEST)
        payout.status = 'pending'
        payout.retry_count += 1
        payout.save(update_fields=['status', 'retry_count'])
        services.run_payout(payout.settlement, success=True)
        payout.refresh_from_db()
        return Response(PayoutRecordSerializer(payout).data)
