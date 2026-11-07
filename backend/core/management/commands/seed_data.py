"""
种子数据：一键生成可演示的完整数据集（6 角色用户 + 3 房源 + 全状态订单 + 任务/结算/评价）。

用法：python manage.py seed_data
幂等：按唯一键 update_or_create，可重复执行。
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Notification, Review
from finance.models import PayoutRecord, Settlement
from listings.models import Calendar, Listing, PriceRule
from orders.models import (BookingOrder, CheckinRecord, DepositDeduction,
                           InspectionRecord, OrderStatusLog, PaymentRecord)
from services.models import CleaningTask, RepairTicket
from users.models import Role, User

User = get_user_model()
TODAY = timezone.localdate()


def pic(n):
    """真实摄影配图：Picsum 固定 ID（联网即显示真实照片；前端加载失败会自动回退本地渐变占位）"""
    return f'https://picsum.photos/id/{n}/800/600'


# 一组真实摄影图（Picsum 固定 ID），用作 3 套房源各 3 张封面/场景图
PICSET = [1011, 1015, 1020, 1024, 1025, 1033, 1035, 1039, 1043]


class Command(BaseCommand):
    help = '生成 PMS 演示数据'

    @transaction.atomic  # 种子数据要么全部成功要么全部回滚，避免半套数据
    def handle(self, *args, **options):
        self._roles()
        landlord, operator, guest, cleaner, repairer, finance = self._users()
        listings = self._listings(landlord)
        self._calendar(listings)
        orders = self._orders(listings, guest)
        self._checkin_and_inspection(orders)
        self._tasks(orders, listings, cleaner, repairer)
        self._reviews(orders, listings, guest, landlord)
        self._settlement(orders, landlord)
        self._notifications(orders, listings, operator, guest, cleaner)
        self.stdout.write(self.style.SUCCESS('演示数据生成完成'))

    # ---------- 角色与用户 ----------

    def _roles(self):
        for code, label in [('landlord', '房东'), ('operator', '运营'), ('guest', '客人'),
                            ('cleaner', '保洁'), ('repairer', '维修'), ('finance', '财务')]:
            Role.objects.update_or_create(code=code, defaults={'label': label})

    def _users(self):
        """6 个角色演示账号，密码统一 123456"""
        spec = [
            ('landlord', '王房东', 'landlord01'), ('operator', '李运营', 'operator01'),
            ('guest', '张小客', 'guest01'), ('cleaner', '赵清洁', 'cleaner01'),
            ('repairer', '钱维修', 'repairer01'), ('finance', '孙财务', 'finance01'),
        ]
        result = []
        for code, name, username in spec:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={'first_name': name, 'phone': '1380000' + str(random.randint(1000, 9999)),
                          'avatar': f'/img/{username}.svg'},
            )
            user.set_password('123456')
            user.save()
            user.roles.set(Role.objects.filter(code=code))
            result.append(user)
        # 超级管理员（后台用），同时给运营角色
        admin, _ = User.objects.update_or_create(
            username='admin', defaults={'is_staff': True, 'is_superuser': True, 'first_name': '超级管理员'})
        admin.set_password('123456')
        admin.save()
        admin.roles.set(Role.objects.filter(code='operator'))
        return result

    # ---------- 房源与日历 ----------

    def _listings(self, landlord):
        specs = [
            dict(title='大理洱海边的观景 Loft', type='whole', city='大理', district='海东',
                 address='洱海畔 180 度海景房', max_guests=4, bed_count=2, area=68.0,
                 facilities=['海景', '投影仪', '洗衣机', '空调', 'WiFi'],
                 description='推窗即见洱海，日出观景位，适合家庭/情侣度假。'),
            dict(title='杭州西湖文艺一居室', type='room', city='杭州', district='西湖',
                 address='步行 8 分钟到西湖断桥', max_guests=2, bed_count=1, area=45.0,
                 facilities=['近景区', '茶具', '空调', 'WiFi'],
                 description='老房改造，木质暖色调，房东自住楼下。'),
            dict(title='厦门鼓浪屿旁的海景合租房', type='share', city='厦门', district='思明',
                 address='轮渡码头 500 米', max_guests=2, bed_count=1, area=30.0,
                 facilities=['海景', '共用厨房', 'WiFi'],
                 description='性价比之选，房东友好，提供旅行攻略。'),
        ]
        listings = []
        for i, spec in enumerate(specs):
            listing, _ = Listing.objects.update_or_create(
                title=spec['title'],
                defaults={**spec, 'owner': landlord, 'status': 'online',
                          'rating': [4.8, 4.6, 4.9][i], 'rating_count': [56, 23, 88][i],
                          'images': [pic(PICSET[i * 3 + j]) for j in range(3)],
                          'deposit_amount': 500},
            )
            listings.append(listing)
            # 每套房源：基础价 + 周末价
            PriceRule.objects.update_or_create(listing=listing, type='base',
                                               defaults={'price': [399, 328, 199][i]})
            PriceRule.objects.update_or_create(listing=listing, type='weekend',
                                               defaults={'price': [499, 428, 269][i]})
        return listings

    def _calendar(self, listings):
        """过去 30 天 ~ 未来 60 天日历：平日/周末价，初始全部可订（订单占用在 _orders 里改）"""
        for listing in listings:
            base = listing.price_rules.get(type='base').price
            weekend = listing.price_rules.get(type='weekend').price
            for offset in range(-30, 61):
                d = TODAY + timedelta(days=offset)
                price = weekend if d.weekday() >= 5 else base
                Calendar.objects.update_or_create(
                    listing=listing, date=d,
                    defaults={'status': 'available', 'price': price})

    # ---------- 订单（覆盖全状态） ----------

    def _orders(self, listings, guest):
        l1, l2, l3 = listings
        specs = [
            # (房源, 入住, 退房, 状态, 渠道, 取消原因)
            (l1, TODAY - timedelta(days=20), TODAY - timedelta(days=15), 'cancelled', 'self', '客人行程有变'),
            (l1, TODAY - timedelta(days=10), TODAY - timedelta(days=7), 'checked_out', 'self', ''),
            (l2, TODAY - timedelta(days=1), TODAY + timedelta(days=1), 'checked_in', 'meituan', ''),
            (l2, TODAY + timedelta(days=7), TODAY + timedelta(days=10), 'confirmed', 'self', ''),
            (l3, TODAY + timedelta(days=14), TODAY + timedelta(days=16), 'pending_confirm', 'tujia', ''),
            (l3, TODAY + timedelta(days=20), TODAY + timedelta(days=22), 'pending_pay', 'self', ''),
        ]
        orders = []
        for i, (listing, ci, co, status, channel, reason) in enumerate(specs):
            nights = (co - ci).days
            nightly = [{'date': str(ci + timedelta(days=k)),
                        'price': float(Calendar.objects.get(listing=listing, date=ci + timedelta(days=k)).price)}
                       for k in range(nights)]
            subtotal = sum(n['price'] for n in nightly)
            cleaning_fee = 100
            detail = {'nightly': nightly, 'subtotal': subtotal,
                      'cleaning_fee': cleaning_fee, 'service_fee': round(subtotal * 0.08, 2)}
            order, _ = BookingOrder.objects.update_or_create(
                order_no=f'PM{TODAY.strftime("%Y%m%d")}{i:06d}',
                defaults=dict(listing=listing, guest=guest, checkin_date=ci, checkout_date=co,
                              nights=nights, guests_count=2, channel=channel,
                              amount_detail=detail, total_amount=subtotal + cleaning_fee,
                              status=status, cancel_reason=reason),
            )
            OrderStatusLog.objects.get_or_create(
                order=order, from_status='', to_status='pending_pay',
                defaults={'remark': '创建订单'})
            if status != 'pending_pay':  # 非待支付订单都有支付流水
                PaymentRecord.objects.update_or_create(
                    order=order,
                    defaults=dict(amount=order.total_amount, channel='alipay',
                                  trade_no=f'2026{order.id}{i:04d}', status='success',
                                  paid_at=timezone.now() - timedelta(days=(co - TODAY).days + 1)))
            # 占用日历：有效订单（非取消）置已订
            if status != 'cancelled':
                for k in range(nights):
                    Calendar.objects.filter(listing=listing, date=ci + timedelta(days=k)).update(status='booked')
            orders.append(order)
        return orders

    # ---------- 入住登记与查房 ----------

    def _checkin_and_inspection(self, orders):
        # orders[2] 入住中：押金已收
        CheckinRecord.objects.update_or_create(
            order=orders[2],
            defaults=dict(guest_names=['张小客', '王小友'], id_card='3301**********1234',
                          phone='13800001111', deposit_amount=500, deposit_status='held',
                          actual_checkin_at=timezone.now() - timedelta(days=1)))
        # orders[1] 已退房：查房有 80 元定损（空调滤网），押金扣减后退还
        CheckinRecord.objects.update_or_create(
            order=orders[1],
            defaults=dict(guest_names=['张小客'], id_card='3301**********1234',
                          phone='13800001111', deposit_amount=500, deposit_status='deducted',
                          actual_checkin_at=timezone.now() - timedelta(days=10),
                          actual_checkout_at=timezone.now() - timedelta(days=7)))
        inspection, _ = InspectionRecord.objects.update_or_create(
            order=orders[1],
            defaults=dict(items=[
                {'name': '卧室卫生', 'result': 'normal', 'note': '', 'amount': 0},
                {'name': '空调滤网', 'result': 'damage', 'note': '滤网破损', 'amount': 80},
                {'name': '家具完好', 'result': 'normal', 'note': '', 'amount': 0},
            ], damage_total=80, conclusion='fail', inspector=self._operator()))
        # 定损生成押金扣减（关联维修工单，工单在 _tasks 里先建，这里先建扣减再补关联）
        deduction, _ = DepositDeduction.objects.update_or_create(
            inspection=inspection, item='空调滤网破损',
            defaults=dict(amount=80, status='confirmed'))
        # 把扣减关联到维修工单（工单在 _tasks 创建，这里反查）
        ticket = RepairTicket.objects.filter(source='inspection', listing=orders[1].listing).first()
        if ticket:
            deduction.repair_ticket = ticket
            deduction.save()

    def _operator(self):
        return User.objects.get(username='operator01')

    # ---------- 服务任务 ----------

    def _tasks(self, orders, listings, cleaner, repairer):
        l1, l2, l3 = listings
        # orders[1] 的清洁任务：已完成（历史）
        CleaningTask.objects.update_or_create(
            order=orders[1],
            defaults=dict(listing=l1, cleaner=cleaner, task_date=TODAY - timedelta(days=7),
                          slot='morning', status='done', requirement='开窗通风',
                          photos=[pic(1047), pic(1050)],
                          assigned_at=timezone.now() - timedelta(days=8),
                          finished_at=timezone.now() - timedelta(days=7),
                          reviewed_at=timezone.now() - timedelta(days=7)))
        # orders[2] 的清洁任务：明天退房后做，已派工（保洁的"今日/明日任务"）
        CleaningTask.objects.update_or_create(
            order=orders[2],
            defaults=dict(listing=l2, cleaner=cleaner, task_date=TODAY + timedelta(days=1),
                          slot='morning', status='assigned',
                          assigned_at=timezone.now() - timedelta(hours=2)))
        # orders[3] 的清洁任务：10 天后，待派工
        CleaningTask.objects.update_or_create(
            order=orders[3],
            defaults=dict(listing=l2, task_date=TODAY + timedelta(days=10), slot='morning'))
        # 维修工单：查房定损来源 + 客人报修 + 房东报修，覆盖三种状态
        t1, _ = RepairTicket.objects.update_or_create(
            listing=l1, source='inspection', title='空调滤网更换',
            defaults=dict(order=orders[1], desc='查房发现滤网破损，需更换', urgency='normal',
                          repairer=repairer, status='done', cost=80,
                          closed_at=timezone.now() - timedelta(days=6)))
        t2, _ = RepairTicket.objects.update_or_create(
            listing=l2, source='guest', title='热水器出水忽冷忽热',
            defaults=dict(order=orders[2], desc='客人反馈洗澡水温不稳定', urgency='urgent',
                          repairer=repairer, status='doing'))
        RepairTicket.objects.update_or_create(
            listing=l3, source='landlord', title='更换智能门锁电池',
            defaults=dict(desc='门锁低电量报警', urgency='normal', status='pending'))
        # t2 维修期间锁定房源对应日期（演示与房态的联动）
        Calendar.objects.filter(listing=l2, date=TODAY).update(status='locked', lock_reason='热水器维修中')

    # ---------- 评价 ----------

    def _reviews(self, orders, listings, guest, landlord):
        Review.objects.update_or_create(
            order=orders[1], reviewer=guest, type='guest_to_listing',
            defaults=dict(listing=listings[0], reviewee=landlord, rating=5,
                          content='海景绝美，房东回复也很快，下次还来！', images=[pic(1059)]))
        Review.objects.update_or_create(
            order=orders[1], reviewer=landlord, type='landlord_to_guest',
            defaults=dict(listing=listings[0], reviewee=guest, rating=5,
                          content='客人很守约，房间保持得干净，欢迎再来。'))

    # ---------- 结算分账 ----------

    def _settlement(self, orders, landlord):
        last_month = (TODAY.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        order = orders[1]  # 上月已退房订单计入月结
        gross = float(order.total_amount)
        commission = round(gross * 0.08, 2)   # 自营渠道佣金率 8%
        service_cost = 50.0                    # 该单清洁成本
        damage = 0.0                           # 定损已由押金覆盖
        net = round(gross - commission - service_cost - damage, 2)
        settlement, _ = Settlement.objects.update_or_create(
            landlord=landlord, period=last_month,
            defaults=dict(order_count=1, gross=gross, commission=commission,
                          service_cost=service_cost, damage=damage, net_amount=net,
                          status='paid', paid_at=timezone.now() - timedelta(days=2)))
        PayoutRecord.objects.update_or_create(
            settlement=settlement,
            defaults=dict(amount=net, status='success',
                          trade_no=f'PO{last_month.replace("-", "")}001',
                          paid_at=timezone.now() - timedelta(days=2)))

    # ---------- 站内信 ----------

    def _notifications(self, orders, listings, operator, guest, cleaner):
        msgs = [
            (guest, 'order_confirmed', '订单已确认', f'您的订单 {orders[3].order_no} 已确认，请按时入住'),
            (operator, 'order_pending', '新订单待确认', f'订单 {orders[4].order_no} 等待确认'),
            (guest, 'checkout_reminder', '退房提醒', '您的订单明天中午 12:00 前退房，请安排好时间'),
            (cleaner, 'task_assigned', '新清洁任务', f'您有一个新任务：{listings[1].title} 明早上午'),
            (guest, 'review_invite', '评价邀请', '您的住宿已结束，14 天内可发表评价'),
        ]
        for user, event, title, content in msgs:
            Notification.objects.get_or_create(
                user=user, event=event, title=title,
                defaults=dict(content=content, is_read=False))
