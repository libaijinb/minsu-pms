from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from orders.models import BookingOrder
from .models import Notification, Review


class ReviewSerializer(serializers.ModelSerializer):
    """评价序列化器：type_display + 双方昵称"""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.first_name', read_only=True, default='')
    reviewer_avatar = serializers.URLField(source='reviewer.avatar', read_only=True, default='')

    class Meta:
        model = Review
        fields = ['id', 'order', 'listing', 'listing_title', 'type', 'type_display',
                  'rating', 'content', 'images', 'reply', 'reply_at',
                  'reviewer_name', 'reviewer_avatar', 'created_at']


class ReviewCreateSerializer(serializers.Serializer):
    """
    提交评价：校验订单归属、已退房、14 天内、未重复评价（BR-REV-01/02）。
    客人评房源（guest_to_listing）或房东评客人（landlord_to_guest）。
    order 传订单号（order_no）而非主键——前端手里只有订单号。
    """

    order = serializers.CharField(label='订单号')
    type = serializers.ChoiceField(choices=['guest_to_listing', 'landlord_to_guest'])
    rating = serializers.IntegerField(min_value=1, max_value=5)
    content = serializers.CharField(max_length=1000, required=False, default='')
    images = serializers.ListField(child=serializers.URLField(), required=False, default=list)

    def validate_order(self, value):
        order = BookingOrder.objects.filter(order_no=value).first()
        if not order:
            raise serializers.ValidationError('订单不存在')
        return order

    def validate(self, attrs):
        user = self.context['request'].user
        order = attrs['order']
        rtype = attrs['type']
        if rtype == 'guest_to_listing':
            if order.guest != user:
                raise serializers.ValidationError({'order': '只能评价自己的订单'})
            reviewee = order.listing.owner
        else:
            if order.listing.owner != user:
                raise serializers.ValidationError({'order': '只能评价自己房源的订单'})
            reviewee = order.guest
        if order.status not in ('checked_out', 'settled'):
            raise serializers.ValidationError({'order': '订单退房后才能评价'})
        if timezone.localdate() - order.checkout_date > timedelta(days=14):
            raise serializers.ValidationError({'order': '退房超过 14 天，评价通道已关闭'})
        if Review.objects.filter(order=order, reviewer=user).exists():
            raise serializers.ValidationError({'order': '你已评价过该订单'})
        attrs['listing'] = order.listing
        attrs['reviewee'] = reviewee
        return attrs

    def create(self, validated_data):
        return Review.objects.create(reviewer=self.context['request'].user, **validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'event', 'title', 'content', 'is_read', 'created_at']
