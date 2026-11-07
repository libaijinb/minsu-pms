"""
房源定时任务：
- backfill_calendar：每小时为已上架房源补齐未来 365 天日历（BR-CAL-07 懒生成 + 定时补漏）
"""

from celery import shared_task

from .models import Listing
from .services import ensure_calendar


@shared_task
def backfill_calendar():
    """日历补漏：只补缺失日期，不覆盖已有行"""
    total = 0
    for listing in Listing.objects.filter(status='online'):
        total += ensure_calendar(listing, days=365)
    return f'backfilled {total} calendar rows'
