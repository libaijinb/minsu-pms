from django.conf import settings
from django.db import models


class Listing(models.Model):
    """
    房源：PMS 的核心库存资源，所有业务（日历/订单/任务/结算）都围绕它展开。
    状态机：草稿 → 审核中 → 已上架 ⇄ 已下架（BR-LST-01）。
    """

    STATUS_CHOICES = [('draft', '草稿'), ('pending', '审核中'), ('online', '已上架'), ('offline', '已下架')]
    TYPE_CHOICES = [('whole', '整套房源'), ('room', '独立房间'), ('share', '合租间')]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='listings', verbose_name='房东')
    title = models.CharField('房源标题', max_length=100)
    type = models.CharField('房源类型', max_length=10, choices=TYPE_CHOICES, default='whole')
    area = models.DecimalField('面积(㎡)', max_digits=6, decimal_places=1, default=0)
    max_guests = models.PositiveSmallIntegerField('可住人数', default=2)
    bed_count = models.PositiveSmallIntegerField('床位数', default=1)
    province = models.CharField('省', max_length=20, default='')
    city = models.CharField('城市', max_length=20, default='')
    district = models.CharField('区/县', max_length=20, default='')
    address = models.CharField('详细地址', max_length=200, default='')
    description = models.TextField('房源描述', blank=True, default='')
    facilities = models.JSONField('设施标签', default=list)   # ["WiFi","空调","洗衣机"]
    images = models.JSONField('图片', default=list)           # ["https://..."]
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='draft')
    rating = models.DecimalField('评分', max_digits=2, decimal_places=1, default=0)  # 均分，评价后回写
    rating_count = models.PositiveIntegerField('评价数', default=0)
    deposit_amount = models.DecimalField('默认押金', max_digits=10, decimal_places=2, default=500)  # 入住登记时按此收取
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '房源'
        verbose_name_plural = '房源'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Calendar(models.Model):
    """
    日历/库存：一行 = 某房源某一晚。日期粒度是「晚」（BR-CAL-01），
    date=D 表示 D 当晚的住宿权；退房日当天下午可再售（换客日）。
    (listing, date) 唯一约束是防超售的最后一道防线（BR-ORD-02）。
    """

    STATUS_CHOICES = [('available', '可订'), ('booked', '已订'), ('locked', '已锁定'), ('closed', '已关闭')]

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='calendar', verbose_name='房源')
    date = models.DateField('日期')
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='available')
    price = models.DecimalField('当晚价', max_digits=8, decimal_places=2, default=0)  # 生成时按价格规则算好快照
    lock_reason = models.CharField('锁定/关闭原因', max_length=100, blank=True, default='')

    class Meta:
        verbose_name = '日历'
        verbose_name_plural = '日历'
        unique_together = [('listing', 'date')]  # 防超售：同一房源同一晚只能有一行
        ordering = ['date']

    def __str__(self):
        return f'{self.listing_id} {self.date} {self.status}'


class PriceRule(models.Model):
    """
    价格规则：五类合一（基础价/周末价/节假日/指定日期/连住折扣）。
    计算优先级：指定日期价 > 节假日价 > 周末价 > 基础价（BR-CAL-03）；
    连住折扣按门槛取一档不叠加（BR-CAL-04）。
    """

    TYPE_CHOICES = [
        ('base', '基础价'),
        ('weekend', '周末价'),
        ('holiday', '节假日价'),
        ('special_date', '指定日期价'),
        ('longstay', '连住折扣'),
    ]

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='price_rules', verbose_name='房源')
    type = models.CharField('规则类型', max_length=15, choices=TYPE_CHOICES)
    price = models.DecimalField('价格', max_digits=8, decimal_places=2, null=True, blank=True)  # 前四类用
    date = models.DateField('指定日期', null=True, blank=True)          # special_date 用
    start_date = models.DateField('开始日期', null=True, blank=True)    # holiday 用
    end_date = models.DateField('结束日期', null=True, blank=True)      # holiday 用
    min_nights = models.PositiveSmallIntegerField('最少连住晚数', null=True, blank=True)  # longstay 用
    discount_rate = models.DecimalField('折扣率', max_digits=3, decimal_places=2, null=True, blank=True)  # longstay 用，如 0.90
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '价格规则'
        verbose_name_plural = '价格规则'

    def __str__(self):
        return f'{self.listing_id} {self.get_type_display()}'
