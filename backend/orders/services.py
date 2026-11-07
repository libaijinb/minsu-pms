"""
订单域业务逻辑层：状态机、日历占房/释放、退房触发链。
技术难点落地（需求分析第 5 章 + BR-ORD-01~08）：
- 转换表驱动状态机，非法转换直接抛 InvalidTransition
- 占房用「条件更新」：UPDATE ... WHERE status='可订'，并发抢同一晚只有一单成功
- 退房副作用集中在一处：生成清洁任务 + 通知（幂等可重试）
"""

import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from listings.models import Calendar
from orders.models import BookingOrder, OrderStatusLog, PaymentRecord
from services.models import CleaningTask

# 订单状态机转换表：当前状态 -> {动作: 目标状态}（BR-ORD-01）
TRANSITIONS = {
    'pending_pay': {'pay': 'pending_confirm', 'cancel': 'cancelled'},
    'pending_confirm': {'confirm': 'confirmed', 'cancel': 'cancelled'},
    'confirmed': {'checkin': 'checked_in', 'cancel': 'cancelled', 'noshow': 'cancelled'},
    'checked_in': {'checkout': 'checked_out'},
    'checked_out': {'dispute': 'disputed', 'settle': 'settled'},
    'disputed': {'resolve': 'checked_out'},
    'cancelled': {},
    'settled': {},
}

PAY_TIMEOUT_MINUTES = 15   # 支付超时（FR-ORD-04）
AUTO_CONFIRM_HOURS = 24    # 房东超时未确认自动确认（BR-ORD-05）


class InvalidTransition(Exception):
    """非法状态转换"""


class CalendarConflict(Exception):
    """日历冲突：所选晚不可订（含并发抢占）"""


def transition(order, action, operator=None, remark=''):
    """
    执行状态转换：校验合法性 -> 更新状态 -> 写流水。
    副作用（通知/任务生成）由调用方在转换成功后显式执行，不散落。
    """
    targets = TRANSITIONS.get(order.status, {})
    to_status = targets.get(action)
    if not to_status:
        raise InvalidTransition(f'订单 {order.status} 不允许执行 {action}')
    from_status = order.status
    order.status = to_status
    order.save(update_fields=['status', 'updated_at'])
    OrderStatusLog.objects.create(order=order, from_status=from_status,
                                  to_status=to_status, operator=operator, remark=remark)
    return to_status


def occupy_calendar(listing, checkin_date, checkout_date):
    """
    占用 [checkin, checkout) 内所有晚（BR-CAL-01：晚粒度，退房日当晚可再售）。
    双重防线：① count 预检给出友好提示 ② 条件 UPDATE（WHERE status='可订'）是原子防线，
    并发下两个请求同时抢同一晚，只有一条 UPDATE 影响行数达标（BR-ORD-02）。
    """
    nights = (checkout_date - checkin_date).days
    dates = [checkin_date + timedelta(days=k) for k in range(nights)]
    available = Calendar.objects.filter(listing=listing, date__in=dates, status='available')
    if available.count() != nights:
        raise CalendarConflict('所选日期包含不可预订的晚，请重新选择')
    updated = available.update(status='booked')  # 单条原子 UPDATE，行锁保证并发安全
    if updated != nights:
        raise CalendarConflict('手慢了，部分日期刚被其他客人订走')


def release_calendar(listing, checkin_date, checkout_date):
    """取消/no-show 时释放占用的晚回「可订」"""
    Calendar.objects.filter(listing=listing, date__gte=checkin_date,
                            date__lt=checkout_date, status='booked').update(status='available')


@transaction.atomic
def create_order(guest, listing, checkin_date, checkout_date, guests_count, channel='self'):
    """创建订单：占房与建订单同事务，任一失败整体回滚"""
    from listings.services import calc_amount

    nights = (checkout_date - checkin_date).days
    if nights <= 0:
        raise CalendarConflict('退房日期必须晚于入住日期')
    amount = calc_amount(listing, checkin_date, checkout_date)
    # 订单号：PM + 日期 + 6 位随机数（BR-ORD-08），唯一约束兜底
    order_no = 'PM' + timezone.localdate().strftime('%Y%m%d') + f'{random.randint(100000, 999999)}'
    order = BookingOrder.objects.create(
        order_no=order_no, listing=listing, guest=guest,
        checkin_date=checkin_date, checkout_date=checkout_date,
        nights=nights, guests_count=guests_count, channel=channel,
        amount_detail=amount, total_amount=amount['total'], status='pending_pay')
    OrderStatusLog.objects.create(order=order, from_status='', to_status='pending_pay',
                                  operator=guest, remark='创建订单')
    occupy_calendar(listing, checkin_date, checkout_date)
    return order


def pay_order(order):
    """
    模拟支付：先做状态转换（非法状态直接抛错，不产生脏流水），
    成功后再记支付流水；trade_no 加随机位防同秒撞唯一约束（NFR-SEC-04）。
    """
    transition(order, 'pay', remark='模拟支付成功')
    trade_no = 'AL' + order.order_no + str(int(timezone.now().timestamp())) + str(random.randint(1000, 9999))
    record = PaymentRecord.objects.create(
        order=order, amount=order.total_amount, channel='alipay',
        trade_no=trade_no, status='success', paid_at=timezone.now())
    return record


def refund_amount(order):
    """
    按取消政策计算应退金额（BR-ORD-04）：
    - 待支付：0（没收过钱）
    - 待确认：全额退（未确认不扣款）
    - 已确认：入住前 3 天（含）全额退；3 天内扣首晚房费 50%
    """
    if order.status in ('pending_pay', 'cancelled', 'settled'):
        return 0
    if order.status == 'pending_confirm':
        return order.total_amount
    days_before = (order.checkin_date - timezone.localdate()).days
    if days_before >= 3:
        return order.total_amount
    first_night = order.amount_detail['nightly'][0]['price']
    return round(float(order.total_amount) - first_night * 0.5, 2)


@transaction.atomic
def cancel_order(order, operator, reason=''):
    """取消订单：算退款 -> 转状态 -> 释放日历"""
    refund = refund_amount(order)
    transition(order, 'cancel', operator=operator, remark=reason or '取消订单')
    order.refund_amount = refund
    order.cancel_reason = reason
    order.save(update_fields=['refund_amount', 'cancel_reason'])
    release_calendar(order.listing, order.checkin_date, order.checkout_date)
    return refund


def do_checkin(order, operator, guest_names, id_card, phone, deposit_amount):
    """入住登记：写登记信息 + 押金 + 状态转已入住（BR-CIO-01/02）"""
    from orders.models import CheckinRecord

    record = CheckinRecord.objects.create(
        order=order, guest_names=guest_names, id_card=id_card, phone=phone,
        deposit_amount=deposit_amount, deposit_status='held',
        actual_checkin_at=timezone.now())
    transition(order, 'checkin', operator=operator, remark='办理入住登记')
    return record


def do_checkout(order, operator):
    """
    退房（BR-CIO-02）：一个动作触发三件事——
    ① 生成清洁任务（get_or_create 幂等，beat 重跑不重复生成）
    ② 查房任务不建表：已退房且无查房记录的订单即"待查房"（API 查询表达）
    ③ 订单转已退房，其占用日期自退房日晚起释放（换客日，BR-CAL-01）
    """
    transition(order, 'checkout', operator=operator, remark='办理退房')
    CleaningTask.objects.get_or_create(
        order=order,
        defaults=dict(listing=order.listing, task_date=order.checkout_date, slot='morning'))
    # 查房任务不建表：已退房且无查房记录的订单即"待查房"（API 查询表达）
    # 注意：退房不释放任何日历——本订单占用区间 [checkin, checkout) 已自然到期，
    # checkout 日当晚起对新客可售是 Calendar 行本来就没被本订单占用的（换客日，BR-CAL-01）
    if order.checkin and order.checkin.deposit_status == 'held':
        order.checkin.actual_checkout_at = timezone.now()
        order.checkin.save(update_fields=['actual_checkout_at'])
