from django.conf import settings
from django.db import models


class BookingOrder(models.Model):
    """
    订单：状态机驱动（BR-ORD-01），金额快照（amount_detail JSON）保证
    历史订单不受后续改价影响（BR-CAL-06）。
    """

    STATUS_CHOICES = [
        ('pending_pay', '待支付'),
        ('pending_confirm', '待确认'),
        ('confirmed', '已确认'),
        ('checked_in', '已入住'),
        ('checked_out', '已退房'),
        ('disputed', '争议中'),
        ('cancelled', '已取消'),
        ('settled', '已结算'),
    ]
    CHANNEL_CHOICES = [('self', '自营'), ('meituan', '美团'), ('tujia', '途家')]

    order_no = models.CharField('订单号', max_length=20, unique=True)  # PM + 日期 + 6 位随机数（BR-ORD-08）
    listing = models.ForeignKey('listings.Listing', on_delete=models.PROTECT, related_name='orders', verbose_name='房源')
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders', verbose_name='客人')
    settlement = models.ForeignKey('finance.Settlement', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='orders', verbose_name='所属结算单')
    checkin_date = models.DateField('入住日期')
    checkout_date = models.DateField('退房日期')
    nights = models.PositiveSmallIntegerField('晚数')
    guests_count = models.PositiveSmallIntegerField('入住人数', default=1)
    channel = models.CharField('渠道', max_length=10, choices=CHANNEL_CHOICES, default='self')
    amount_detail = models.JSONField('金额明细快照')  # {nightly:[{date,price}], discount, cleaning_fee, service_fee, total}
    total_amount = models.DecimalField('订单总额', max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField('已退金额', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('状态', max_length=15, choices=STATUS_CHOICES, default='pending_pay')
    cancel_reason = models.CharField('取消原因', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'created_at'])]

    def __str__(self):
        return self.order_no


class OrderStatusLog(models.Model):
    """订单状态流水：每次状态转换必写一条（BR-ORD-07），可追溯、可对账"""

    order = models.ForeignKey(BookingOrder, on_delete=models.CASCADE, related_name='logs', verbose_name='订单')
    from_status = models.CharField('原状态', max_length=15, blank=True, default='')  # 创建时为 ''
    to_status = models.CharField('新状态', max_length=15)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, verbose_name='操作人')  # null = 系统自动
    remark = models.CharField('备注', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('操作时间', auto_now_add=True)

    class Meta:
        verbose_name = '订单状态流水'
        verbose_name_plural = '订单状态流水'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.order_id} {self.from_status}→{self.to_status}'


class PaymentRecord(models.Model):
    """支付流水：一订单可多笔（失败重试），trade_no 唯一保证回调幂等（NFR-SEC-04）"""

    STATUS_CHOICES = [('init', '待支付'), ('success', '支付成功'), ('refunded', '已退款')]

    order = models.ForeignKey(BookingOrder, on_delete=models.CASCADE, related_name='payments', verbose_name='订单')
    amount = models.DecimalField('金额', max_digits=10, decimal_places=2)
    channel = models.CharField('支付渠道', max_length=10, default='alipay')
    trade_no = models.CharField('交易号', max_length=64, unique=True)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='init')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    paid_at = models.DateTimeField('支付时间', null=True, blank=True)

    class Meta:
        verbose_name = '支付流水'
        verbose_name_plural = '支付流水'
        ordering = ['-created_at']


class CheckinRecord(models.Model):
    """入住登记：1:1 订单，含押金收取与处置（BR-CIO-01/02/03）"""

    DEPOSIT_STATUS_CHOICES = [
        ('unpaid', '未收取'), ('held', '已收取'), ('refunded', '已全额退'), ('deducted', '已扣减'),
    ]

    order = models.OneToOneField(BookingOrder, on_delete=models.CASCADE, related_name='checkin', verbose_name='订单')
    guest_names = models.JSONField('入住人列表')      # ["张三", "李四"]
    id_card = models.CharField('身份证号', max_length=18)
    phone = models.CharField('联系电话', max_length=11)
    deposit_amount = models.DecimalField('押金金额', max_digits=10, decimal_places=2)
    deposit_status = models.CharField('押金状态', max_length=10, choices=DEPOSIT_STATUS_CHOICES, default='unpaid')
    actual_checkin_at = models.DateTimeField('实际入住时间', null=True, blank=True)
    actual_checkout_at = models.DateTimeField('实际退房时间', null=True, blank=True)
    created_at = models.DateTimeField('登记时间', auto_now_add=True)

    class Meta:
        verbose_name = '入住登记'
        verbose_name_plural = '入住登记'


class InspectionRecord(models.Model):
    """退房查房：1:1 订单。检查项 JSON 化，定损总额是押金扣减与结算扣款的唯一依据（BR-INS-04）"""

    CONCLUSION_CHOICES = [('pass', '合格'), ('fail', '不合格')]

    order = models.OneToOneField(BookingOrder, on_delete=models.CASCADE, related_name='inspection', verbose_name='订单')
    items = models.JSONField('检查项')  # [{name, result:normal/damage, note, amount}]
    damage_total = models.DecimalField('定损总额', max_digits=10, decimal_places=2, default=0)
    conclusion = models.CharField('查房结论', max_length=6, choices=CONCLUSION_CHOICES, default='pass')
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, verbose_name='查房人')
    created_at = models.DateTimeField('查房时间', auto_now_add=True)

    class Meta:
        verbose_name = '查房记录'
        verbose_name_plural = '查房记录'


class DepositDeduction(models.Model):
    """押金扣减明细：逐条可追溯，损坏项关联维修工单（BR-INS-04）"""

    STATUS_CHOICES = [('pending', '待确认'), ('confirmed', '已确认'), ('cancelled', '已取消')]

    inspection = models.ForeignKey(InspectionRecord, on_delete=models.CASCADE,
                                   related_name='deductions', verbose_name='查房记录')
    item = models.CharField('扣款项', max_length=100)
    amount = models.DecimalField('扣减金额', max_digits=10, decimal_places=2)
    repair_ticket = models.ForeignKey('services.RepairTicket', on_delete=models.SET_NULL,
                                      null=True, blank=True, verbose_name='关联维修工单')
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '押金扣减'
        verbose_name_plural = '押金扣减'
