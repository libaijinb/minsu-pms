"""
财务域业务逻辑层：月结计算（BR-STL-01~06）。
公式：房东应得 = 订单实付 − 平台佣金(按渠道率) − 保洁成本 − 损坏赔付(超出押金部分)
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from orders import services as order_services
from orders.models import BookingOrder, DepositDeduction
from services.models import CleaningTask
from .models import PayoutRecord, Settlement

# 渠道佣金率（BR-STL-02，可做成平台配置表）
CHANNEL_RATE = {'self': Decimal('0.08'), 'meituan': Decimal('0.15'), 'tujia': Decimal('0.12')}
CLEANING_UNIT_COST = Decimal('50')  # 每完成一次清洁任务的平台成本


def month_range(period):
    """'YYYY-MM' -> (该月第一天, 下月第一天)"""
    year, month = map(int, period.split('-'))
    start = date(year, month, 1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def last_period():
    """上一个自然月，如当前 2026-10 -> '2026-09'"""
    today = timezone.localdate()
    first = today.replace(day=1)
    return (first - timedelta(days=1)).strftime('%Y-%m')


@transaction.atomic
def settle_period(landlord, period):
    """
    为单个房东结算指定周期：
    1. 找出该房东、已退房、退房日落在本周期、尚未结算的订单
    2. 计算 gross/commission/service_cost/damage/net
    3. 幂等创建结算单（(房东, 周期) 唯一约束）+ 关联订单 + 逐单转「已结算」写流水
    4. 生成待分账记录
    返回 (settlement, created)；无订单可结时返回 (None, False)。
    """
    start, end = month_range(period)
    orders = list(BookingOrder.objects.filter(
        listing__owner=landlord, status='checked_out',
        checkout_date__gte=start, checkout_date__lt=end, settlement__isnull=True))
    if not orders:
        return None, False

    gross = sum(o.total_amount for o in orders)  # Decimal
    commission = sum(o.total_amount * CHANNEL_RATE.get(o.channel, Decimal('0.08')) for o in orders)
    done_task_count = CleaningTask.objects.filter(
        listing__owner=landlord, status='done', task_date__gte=start, task_date__lt=end).count()
    service_cost = done_task_count * CLEANING_UNIT_COST
    # 损坏赔付只计超出押金部分（押金已扣的不重复向房东收）
    damage = Decimal('0')
    for o in orders:
        if hasattr(o, 'inspection') and o.checkin:
            damage += max(Decimal('0'), Decimal(str(o.inspection.damage_total))
                          - Decimal(str(o.checkin.deposit_amount)))
    net = round(float(gross) - float(commission) - float(service_cost) - float(damage), 2)

    settlement, created = Settlement.objects.get_or_create(
        landlord=landlord, period=period,
        defaults=dict(order_count=len(orders), gross=gross, commission=commission,
                      service_cost=service_cost, damage=damage, net_amount=net))
    if not created:
        return settlement, False  # 已结算过，幂等返回
    settlement.orders.set(orders)
    for o in orders:  # 逐单转状态并写流水（月结是系统批量操作，也要可追溯）
        o.settlement = settlement
        o.save(update_fields=['settlement'])
        order_services.transition(o, 'settle', remark=f'{period} 月结自动结算')
    PayoutRecord.objects.create(settlement=settlement, amount=net, status='pending')
    return settlement, True


def run_payout(settlement, success=True, trade_no=''):
    """
    执行分账：演示环境直接成功；真实环境对接微信/支付宝分账接口。
    失败不阻塞：记录失败原因，可重试（BR-STL-05/06）。
    """
    payout = settlement.payouts.filter(status='pending').first()
    if not payout:
        return None
    if success:
        payout.status = 'success'
        payout.trade_no = trade_no or f'PO{settlement.period.replace("-", "")}{settlement.id:04d}'
        payout.paid_at = timezone.now()
        settlement.status = 'paid'
        settlement.paid_at = timezone.now()
    else:
        payout.status = 'failed'
        payout.fail_reason = '模拟分账失败'
        settlement.status = 'failed'
    payout.save()
    settlement.save(update_fields=['status', 'paid_at'])
    return payout
