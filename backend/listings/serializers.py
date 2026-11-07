from rest_framework import serializers

from .models import Calendar, Listing, PriceRule


class ListingSerializer(serializers.ModelSerializer):
    """
    房源序列化器：一套字段同时服务 C 端浏览与 B 端管理。
    status 只读——上下架/审核走专用接口，避免普通编辑误改状态。
    """

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    owner_name = serializers.CharField(source='owner.first_name', read_only=True, default='')
    owner_avatar = serializers.URLField(source='owner.avatar', read_only=True, default='')

    class Meta:
        model = Listing
        fields = ['id', 'title', 'type', 'type_display', 'area', 'max_guests', 'bed_count',
                  'province', 'city', 'district', 'address', 'description', 'facilities',
                  'images', 'status', 'status_display', 'rating', 'rating_count',
                  'deposit_amount', 'owner', 'owner_name', 'owner_avatar', 'created_at']
        read_only_fields = ['id', 'owner', 'status', 'rating', 'rating_count', 'created_at']

    def validate_title(self, value):
        """同一房东下房源标题不可重复（与项目查重同思路，BR-LST 系列）"""
        user = self.context['request'].user
        qs = Listing.objects.filter(owner=user, title=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('你已有同名房源')
        return value


class CalendarSerializer(serializers.ModelSerializer):
    """日历行：一晚一行，date=D 表示 D 当晚（BR-CAL-01）"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Calendar
        fields = ['id', 'date', 'status', 'status_display', 'price', 'lock_reason']


class PriceRuleSerializer(serializers.ModelSerializer):
    """价格规则：五类（base/weekend/holiday/special_date/longstay）"""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)

    class Meta:
        model = PriceRule
        fields = ['id', 'listing', 'listing_title', 'type', 'type_display', 'price', 'date',
                  'start_date', 'end_date', 'min_nights', 'discount_rate', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """按规则类型校验必填字段，避免脏数据"""
        rtype = attrs.get('type', self.instance.type if self.instance else '')
        if rtype == 'special_date' and not attrs.get('date'):
            raise serializers.ValidationError({'date': '指定日期价必须选择日期'})
        if rtype == 'holiday' and not (attrs.get('start_date') and attrs.get('end_date')):
            raise serializers.ValidationError({'start_date': '节假日价必须填写起止日期'})
        if rtype == 'longstay' and not (attrs.get('min_nights') and attrs.get('discount_rate')):
            raise serializers.ValidationError({'min_nights': '连住折扣必须填写最少晚数与折扣率'})
        if rtype in ('base', 'weekend', 'special_date', 'holiday') and not attrs.get('price'):
            raise serializers.ValidationError({'price': '该规则类型必须填写价格'})
        return attrs
