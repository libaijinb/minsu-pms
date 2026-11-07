import calendar as calendar_lib
from datetime import date

from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Calendar, Listing
from orders.models import BookingOrder
from users.permissions import IsLandlordOrOperator
from .models import Notification, Review
from .serializers import (NotificationSerializer, ReviewCreateSerializer,
                          ReviewSerializer)


class ReviewViewSet(viewsets.GenericViewSet):
    """
    评价：
    - GET /api/reviews/?listing=<id> 房源评价列表（公开）
    - POST /api/reviews/ 提交评价（校验见 serializer）
    - POST /api/reviews/{id}/reply/ 房东回复
    """

    queryset = Review.objects.select_related('listing', 'reviewer').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_permissions(self):
        if self.action in ('create', 'reply'):
            return [IsAuthenticated()]
        return []  # 列表公开

    def list(self, request):
        listing_id = request.query_params.get('listing')
        rtype = request.query_params.get('type', 'guest_to_listing')
        qs = self.get_queryset().filter(type=rtype).order_by('-created_at')
        if listing_id:
            qs = qs.filter(listing_id=listing_id)
        page = self.paginate_queryset(qs)
        serializer = ReviewSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def create(self, request):
        serializer = ReviewCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        # 评价后回写房源均分（FR-REV-04）
        if review.type == 'guest_to_listing':
            agg = Review.objects.filter(listing=review.listing, type='guest_to_listing').aggregate(
                avg=Avg('rating'), cnt=Count('id'))
            review.listing.rating = round(agg['avg'] or 0, 1)
            review.listing.rating_count = agg['cnt']
            review.listing.save(update_fields=['rating', 'rating_count'])
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """房东回复自己房源下的评价"""
        review = get_object_or_404(Review, pk=pk)
        if review.listing.owner != request.user and not request.user.is_superuser:
            return Response({'detail': '只能回复自己房源的评价'}, status=status.HTTP_403_FORBIDDEN)
        review.reply = request.data.get('reply', '')
        review.reply_at = timezone.now()
        review.save(update_fields=['reply', 'reply_at'])
        return Response(ReviewSerializer(review).data)


class NotificationViewSet(viewsets.GenericViewSet):
    """站内信：我的通知列表 + 单条已读 + 全部已读"""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request):
        unread_only = request.query_params.get('unread') == '1'
        qs = self.get_queryset()
        if unread_only:
            qs = qs.filter(is_read=False)
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(NotificationSerializer(page, many=True).data)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notification = get_object_or_404(self.get_queryset(), pk=pk)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'detail': '已读'})

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'detail': '全部已读'})


class StatsView(APIView):
    """
    经营统计（FR-RPT-01/02）：OCC / ADR / RevPAR 近 6 个月趋势 + 渠道占比。
    房东看自己房源，运营看全平台。BR-RPT-01/02。
    """

    permission_classes = [IsLandlordOrOperator]

    def get(self, request):
        user = request.user
        listings = Listing.objects.all() if user.roles.filter(code='operator').exists() or user.is_superuser \
            else Listing.objects.filter(owner=user)
        today = timezone.localdate()
        trend = []
        for offset in range(5, -1, -1):
            # 逐月迭代（不依赖 dateutil）
            y, m = today.year, today.month - offset
            while m <= 0:
                m += 12
                y -= 1
            days_in_month = calendar_lib.monthrange(y, m)[1]
            start, end = date(y, m, 1), date(y, m, days_in_month)
            cals = Calendar.objects.filter(listing__in=listings, date__range=[start, end])
            available = cals.exclude(status='closed').count()
            sold = cals.filter(status='booked').count()
            revenue = float(BookingOrder.objects.filter(
                listing__in=listings, status__in=['checked_out', 'checked_in', 'settled'],
                checkin_date__lte=end, checkout_date__gt=start
            ).aggregate(s=Sum('total_amount'))['s'] or 0)
            trend.append({
                'month': f'{y}-{m:02d}',
                'occ': round(sold / available * 100, 1) if available else 0,
                'adr': round(revenue / sold, 2) if sold else 0,
                'revpar': round(revenue / available, 2) if available else 0,
            })
        # 渠道占比（订单数）
        channel_qs = BookingOrder.objects.filter(listing__in=listings).values('channel').annotate(
            cnt=Count('id')).order_by('-cnt')
        return Response({'trend': trend, 'channels': list(channel_qs)})
