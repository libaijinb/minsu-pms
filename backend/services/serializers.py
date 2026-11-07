from rest_framework import serializers

from .models import CleaningTask, RepairTicket


class CleaningTaskSerializer(serializers.ModelSerializer):
    """清洁任务序列化器：B 端（运营/房东）与保洁端共用"""

    slot_display = serializers.CharField(source='get_slot_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_address = serializers.CharField(source='listing.address', read_only=True)
    cleaner_name = serializers.CharField(source='cleaner.first_name', read_only=True, default='')
    order_no = serializers.CharField(source='order.order_no', read_only=True)

    class Meta:
        model = CleaningTask
        fields = ['id', 'order', 'order_no', 'listing', 'listing_title', 'listing_address',
                  'cleaner', 'cleaner_name', 'task_date', 'slot', 'slot_display',
                  'status', 'status_display', 'requirement', 'photos',
                  'finished_at', 'reviewed_at', 'created_at']
        read_only_fields = ['id', 'status', 'photos', 'finished_at', 'reviewed_at', 'created_at']


class CleaningDispatchSerializer(serializers.Serializer):
    """派工入参：cleaner + task_date + slot，(保洁,日期,时段) 唯一约束物理防冲突（BR-CLN-03）"""

    cleaner = serializers.IntegerField(label='保洁用户 ID')
    task_date = serializers.DateField()
    slot = serializers.ChoiceField(choices=[('morning', '上午'), ('afternoon', '下午')])


class CleaningFinishSerializer(serializers.Serializer):
    """保洁完成入参：至少 1 张照片（BR-CLN-05）"""

    photos = serializers.ListField(child=serializers.URLField(), min_length=1)


class RepairTicketSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_address = serializers.CharField(source='listing.address', read_only=True)
    repairer_name = serializers.CharField(source='repairer.first_name', read_only=True, default='')
    order_no = serializers.SerializerMethodField()

    class Meta:
        model = RepairTicket
        fields = ['id', 'listing', 'listing_title', 'listing_address', 'order', 'order_no',
                  'source', 'source_display', 'title', 'desc', 'urgency', 'urgency_display',
                  'images', 'repairer', 'repairer_name', 'status', 'status_display',
                  'cost', 'created_at', 'closed_at']
        read_only_fields = ['id', 'source', 'status', 'cost', 'closed_at', 'created_at']

    def get_order_no(self, obj):
        return obj.order.order_no if obj.order else ''


class RepairCreateSerializer(serializers.ModelSerializer):
    """报修入参：客人/房东/运营创建"""

    class Meta:
        model = RepairTicket
        fields = ['listing', 'order', 'title', 'desc', 'urgency', 'images']

    def validate(self, attrs):
        # 客人只能给自己的订单报修
        user = self.context['request'].user
        if user.roles.filter(code='guest').exists() and not user.is_superuser:
            order = attrs.get('order')
            if not order or order.guest != user:
                raise serializers.ValidationError({'order': '客人只能为自己的订单报修'})
        return attrs


class RepairDispatchSerializer(serializers.Serializer):
    repairer = serializers.IntegerField(label='维修用户 ID')


class RepairHandleSerializer(serializers.Serializer):
    """维修处理结果：费用 + 说明"""

    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    note = serializers.CharField(max_length=500, required=False, default='')
