from rest_framework import serializers

from .models import PayoutRecord, Settlement


class PayoutRecordSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PayoutRecord
        fields = ['id', 'amount', 'status', 'status_display', 'trade_no',
                  'fail_reason', 'retry_count', 'created_at', 'paid_at']


class SettlementSerializer(serializers.ModelSerializer):
    """结算单：房东/财务视角共用"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    landlord_name = serializers.CharField(source='landlord.first_name', read_only=True, default='')

    class Meta:
        model = Settlement
        fields = ['id', 'landlord', 'landlord_name', 'period', 'order_count', 'gross',
                  'commission', 'service_cost', 'damage', 'net_amount', 'status',
                  'status_display', 'created_at', 'paid_at']


class SettlementDetailSerializer(SettlementSerializer):
    """结算单详情：附订单明细与分账记录"""

    orders = serializers.SerializerMethodField()
    payouts = PayoutRecordSerializer(many=True, read_only=True)

    class Meta(SettlementSerializer.Meta):
        fields = SettlementSerializer.Meta.fields + ['orders', 'payouts']

    def get_orders(self, obj):
        return [{'order_no': o.order_no, 'listing_title': o.listing.title,
                 'checkout_date': o.checkout_date, 'total_amount': o.total_amount,
                 'channel': o.channel} for o in obj.orders.select_related('listing').all()]
