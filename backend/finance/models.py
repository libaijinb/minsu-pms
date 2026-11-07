from django.conf import settings
from django.db import models


class Settlement(models.Model):
    """
    月结算单：公式 房东应得 = 订单实付 − 佣金(按渠道率) − 保洁成本 − 损坏赔付（BR-STL-01）。
    (landlord, period) 唯一约束保证月结幂等，重复执行不重复结算（BR-STL-04）。
    """

    STATUS_CHOICES = [
        ('pending', '待分账'), ('paying', '分账中'), ('paid', '已分账'), ('failed', '分账失败'),
    ]

    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='settlements', verbose_name='房东')
    period = models.CharField('结算周期', max_length=7)  # 'YYYY-MM'
    order_count = models.PositiveIntegerField('订单数', default=0)
    gross = models.DecimalField('订单实付合计', max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField('平台佣金', max_digits=10, decimal_places=2, default=0)
    service_cost = models.DecimalField('保洁成本', max_digits=10, decimal_places=2, default=0)
    damage = models.DecimalField('损坏赔付', max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField('房东应得', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    paid_at = models.DateTimeField('分账完成时间', null=True, blank=True)

    class Meta:
        verbose_name = '结算单'
        verbose_name_plural = '结算单'
        unique_together = [('landlord', 'period')]  # 幂等：一个房东一个周期只有一单
        ordering = ['-period']

    def __str__(self):
        return f'{self.landlord_id} {self.period}'


class PayoutRecord(models.Model):
    """分账记录：逐笔留状态与流水号，失败可重试且不阻塞月结主流程（BR-STL-05/06）"""

    STATUS_CHOICES = [('pending', '待分账'), ('success', '分账成功'), ('failed', '分账失败')]

    settlement = models.ForeignKey(Settlement, on_delete=models.CASCADE,
                                   related_name='payouts', verbose_name='结算单')
    amount = models.DecimalField('分账金额', max_digits=10, decimal_places=2)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='pending')
    trade_no = models.CharField('分账流水号', max_length=64, blank=True, default='')
    fail_reason = models.CharField('失败原因', max_length=200, blank=True, default='')
    retry_count = models.PositiveSmallIntegerField('重试次数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    paid_at = models.DateTimeField('分账时间', null=True, blank=True)

    class Meta:
        verbose_name = '分账记录'
        verbose_name_plural = '分账记录'
        ordering = ['-created_at']
