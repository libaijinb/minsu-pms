from django.utils import timezone
from rest_framework import serializers

from listings.models import Listing
from .models import (BookingOrder, CheckinRecord, InspectionRecord,
                     OrderStatusLog, PaymentRecord)


class PaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PaymentRecord
        fields = ['id', 'amount', 'channel', 'trade_no', 'status', 'status_display', 'paid_at']


class OrderStatusLogSerializer(serializers.ModelSerializer):
    """状态流水：operator 为 null 表示系统自动操作（定时任务等）"""

    operator_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusLog
        fields = ['id', 'from_status', 'to_status', 'operator_name', 'remark', 'created_at']

    def get_operator_name(self, obj):
        return obj.operator.first_name if obj.operator else '系统'


class CheckinSerializer(serializers.ModelSerializer):
    deposit_status_display = serializers.CharField(source='get_deposit_status_display', read_only=True)

    class Meta:
        model = CheckinRecord
        fields = ['id', 'guest_names', 'id_card', 'phone', 'deposit_amount',
                  'deposit_status', 'deposit_status_display',
                  'actual_checkin_at', 'actual_checkout_at']


class InspectionSerializer(serializers.ModelSerializer):
    conclusion_display = serializers.CharField(source='get_conclusion_display', read_only=True)
    inspector_name = serializers.SerializerMethodField()

    class Meta:
        model = InspectionRecord
        fields = ['id', 'items', 'damage_total', 'conclusion', 'conclusion_display',
                  'inspector_name', 'created_at']

    def get_inspector_name(self, obj):
        return obj.inspector.first_name if obj.inspector else ''


class OrderSerializer(serializers.ModelSerializer):
    """订单列表项：轻量字段，C/B 端通用"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_image = serializers.SerializerMethodField()
    guest_name = serializers.CharField(source='guest.first_name', read_only=True, default='')

    class Meta:
        model = BookingOrder
        fields = ['order_no', 'listing', 'listing_title', 'listing_image', 'checkin_date',
                  'checkout_date', 'nights', 'guests_count', 'total_amount', 'status',
                  'status_display', 'channel', 'channel_display', 'guest_name', 'created_at']

    def get_listing_image(self, obj):
        return obj.listing.images[0] if obj.listing.images else ''


class OrderDetailSerializer(OrderSerializer):
    """订单详情：金额快照明细 + 入住/查房/支付/流水/清洁任务全量信息"""

    guest_phone = serializers.CharField(source='guest.phone', read_only=True, default='')
    checkin = CheckinSerializer(read_only=True)
    inspection = InspectionSerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    logs = OrderStatusLogSerializer(many=True, read_only=True)
    cleaning = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + [
            'amount_detail', 'refund_amount', 'cancel_reason', 'updated_at',
            'guest_phone', 'checkin', 'inspection', 'payments', 'logs', 'cleaning',
        ]

    def get_cleaning(self, obj):
        task = getattr(obj, 'cleaning_task', None)
        if not task:
            return None
        return {'status': task.status, 'task_date': task.task_date, 'slot': task.slot,
                'cleaner_name': task.cleaner.first_name if task.cleaner else None}


class OrderCreateSerializer(serializers.Serializer):
    """创建订单入参：基本校验在此，可订性/金额由 services 层在事务内完成"""

    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())
    checkin_date = serializers.DateField()
    checkout_date = serializers.DateField()
    guests_count = serializers.IntegerField(min_value=1, default=1)
    channel = serializers.ChoiceField(choices=['self', 'meituan', 'tujia'], default='self')

    def validate(self, attrs):
        listing = attrs['listing']
        ci, co = attrs['checkin_date'], attrs['checkout_date']
        if co <= ci:
            raise serializers.ValidationError({'checkout_date': '退房日期必须晚于入住日期'})
        if ci < timezone.localdate():
            raise serializers.ValidationError({'checkin_date': '入住日期不能早于今天'})
        if attrs['guests_count'] > listing.max_guests:
            raise serializers.ValidationError({'guests_count': f'该房源最多住 {listing.max_guests} 人'})
        if listing.status != 'online':
            raise serializers.ValidationError({'listing': '房源未上架，暂不可预订'})
        return attrs


class CheckinCreateSerializer(serializers.Serializer):
    """入住登记入参"""

    guest_names = serializers.ListField(child=serializers.CharField(max_length=50), min_length=1)
    id_card = serializers.CharField(max_length=18)
    phone = serializers.CharField(max_length=11)
    deposit_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate_id_card(self, value):
        if not (value.isdigit() and len(value) in (15, 18)):
            raise serializers.ValidationError('身份证号格式不正确')
        return value

    def validate_phone(self, value):
        if not (value.isdigit() and len(value) == 11):
            raise serializers.ValidationError('手机号格式不正确')
        return value


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=False, default='')
