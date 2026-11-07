"""
房源域业务逻辑层：价格引擎 + 日历生成。
规则见需求分析 BR-CAL-01~08：晚价优先级 指定日期 > 节假日 > 周末 > 基础；连住折扣取一档。
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Calendar, Listing, PriceRule

PLATFORM_CLEANING_FEE = 100      # 平台清洁费（一次性，演示固定值，可做成配置）
SELF_CHANNEL_SERVICE_RATE = 0.08  # 自营渠道平台服务费率（房东承担，计入结算）


def calc_nightly_price(listing, day):
    """
    计算某房源某晚价格。规则一次性查回再匹配，避免每晚一次查询。
    同级多条规则取最后配置的一条（后配置覆盖先配置）。
    """
    rules = listing.price_rules.all()
    base = weekend = special = holiday = None
    for r in rules:
        if r.type == 'base':
            base = r.price
        elif r.type == 'weekend':
            weekend = r.price
        elif r.type == 'special_date' and r.date == day:
            special = r.price
        elif r.type == 'holiday' and r.start_date and r.end_date and r.start_date <= day <= r.end_date:
            holiday = r.price
    if special is not None:
        return special
    if holiday is not None:
        return holiday
    if weekend is not None and day.weekday() >= 5:  # 周六/周日算周末
        return weekend
    return base or 0


def calc_discount_rate(listing, nights):
    """连住折扣：匹配满足门槛的最高一档，只取一档不叠加（BR-CAL-04）"""
    rule = (listing.price_rules
            .filter(type='longstay', min_nights__lte=nights, discount_rate__isnull=False)
            .order_by('-min_nights').first())
    return rule.discount_rate if rule else None


def calc_amount(listing, checkin_date, checkout_date):
    """
    计算订单金额并返回快照明细。客人下单时冻结进订单（BR-CAL-06），
    之后房东改价不影响历史订单。
    """
    nights = (checkout_date - checkin_date).days
    nightly = []
    for k in range(nights):
        d = checkin_date + timedelta(days=k)
        nightly.append({'date': str(d), 'price': float(calc_nightly_price(listing, d))})
    subtotal = round(sum(n['price'] for n in nightly), 2)
    rate = calc_discount_rate(listing, nights)
    discount = round(subtotal * (1 - float(rate)), 2) if rate else 0
    cleaning_fee = float(PLATFORM_CLEANING_FEE)
    service_fee = round((subtotal - discount) * SELF_CHANNEL_SERVICE_RATE, 2)  # 房东承担，不进客人实付
    total = round(subtotal - discount + cleaning_fee, 2)
    return {'nights': nights, 'nightly': nightly, 'subtotal': subtotal, 'discount': discount,
            'cleaning_fee': cleaning_fee, 'service_fee': service_fee, 'total': total}


@transaction.atomic
def ensure_calendar(listing, days=365):
    """
    日历补漏：为房源补齐从最早缺失日到未来 days 天的日历行（懒生成 + 定时补漏，BR-CAL-07）。
    只补缺失的日期，不覆盖已有行。
    """
    today = timezone.localdate()
    end = today + timedelta(days=days)
    existing = set(Calendar.objects.filter(listing=listing, date__gte=today).values_list('date', flat=True))
    base_rule = listing.price_rules.filter(type='base').first()
    weekend_rule = listing.price_rules.filter(type='weekend').first()
    base_price = base_rule.price if base_rule else 0
    weekend_price = weekend_rule.price if weekend_rule else base_price
    new_rows = []
    d = today
    while d <= end:
        if d not in existing:
            price = weekend_price if d.weekday() >= 5 else base_price
            new_rows.append(Calendar(listing=listing, date=d, status='available', price=price))
        d += timedelta(days=1)
    Calendar.objects.bulk_create(new_rows)
    return len(new_rows)
