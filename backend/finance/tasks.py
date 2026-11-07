"""
财务定时任务：
- monthly_settlement：每月 1 日凌晨为所有房东结算上月（BR-STL-03）
"""

from celery import shared_task
from django.contrib.auth import get_user_model

from . import services

User = get_user_model()


@shared_task
def monthly_settlement():
    """月结：遍历所有拥有房源的房东，结算上一个自然月"""
    period = services.last_period()
    landlords = User.objects.filter(roles__code='landlord').distinct()
    settled = 0
    for landlord in landlords:
        settlement, created = services.settle_period(landlord, period)
        if created:
            settled += 1
    return f'settled {settled} landlords for {period}'
