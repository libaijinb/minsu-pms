"""
订单定时任务：
- scan_payment_timeout：每分钟扫描超时未支付订单，自动取消并释放日历（FR-ORD-04）
- auto_confirm_orders：24 小时未确认的订单自动确认（BR-ORD-05）

幂等设计：任务重复执行不会产生重复副作用——
取消用条件 update 抢占（只有 pending_pay 状态能被改），自动确认同样先过滤状态。
"""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from . import services
from .models import BookingOrder

PAY_TIMEOUT_MINUTES = services.PAY_TIMEOUT_MINUTES
AUTO_CONFIRM_HOURS = services.AUTO_CONFIRM_HOURS


@shared_task
def scan_payment_timeout():
    """取消超时未支付订单：15 分钟未支付自动取消 + 释放日历"""
    deadline = timezone.now() - timedelta(minutes=PAY_TIMEOUT_MINUTES)
    timeout_orders = BookingOrder.objects.filter(
        status='pending_pay', created_at__lt=deadline)
    cancelled = 0
    for order in timeout_orders:
        try:
            services.cancel_order(order, operator=None, reason='支付超时自动取消')
            cancelled += 1
        except services.InvalidTransition:
            continue  # 并发下已被处理，跳过
    return f'cancelled {cancelled} timeout orders'


@shared_task
def auto_confirm_orders():
    """24 小时未确认的订单自动确认，避免房东不操作影响客人（BR-ORD-05）"""
    deadline = timezone.now() - timedelta(hours=AUTO_CONFIRM_HOURS)
    stale_orders = BookingOrder.objects.filter(
        status='pending_confirm', updated_at__lt=deadline)
    confirmed = 0
    for order in stale_orders:
        try:
            services.transition(order, 'confirm', operator=None, remark='超时自动确认')
            confirmed += 1
        except services.InvalidTransition:
            continue
    return f'auto confirmed {confirmed} orders'
