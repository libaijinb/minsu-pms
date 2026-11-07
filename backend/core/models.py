from django.conf import settings
from django.db import models


class Review(models.Model):
    """
    双向评价：客人评房源 + 房东评客人（BR-REV-01）。
    一方评价后另一方 14 天内未评则关闭，互不公开（BR-REV-02，防止差评要挟）。
    """

    TYPE_CHOICES = [('guest_to_listing', '客人评房源'), ('landlord_to_guest', '房东评客人')]

    order = models.ForeignKey('orders.BookingOrder', on_delete=models.CASCADE,
                              related_name='reviews', verbose_name='订单')
    listing = models.ForeignKey('listings.Listing', on_delete=models.CASCADE,
                                related_name='reviews', verbose_name='房源')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='reviews_written', verbose_name='评价人')
    reviewee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='reviews_received', verbose_name='被评价人')
    type = models.CharField('评价类型', max_length=20, choices=TYPE_CHOICES)
    rating = models.PositiveSmallIntegerField('评分')  # 1-5 星
    content = models.TextField('评价内容', blank=True, default='')
    images = models.JSONField('图片', default=list)
    reply = models.TextField('房东回复', blank=True, default='')
    reply_at = models.DateTimeField('回复时间', null=True, blank=True)
    created_at = models.DateTimeField('评价时间', auto_now_add=True)

    class Meta:
        verbose_name = '评价'
        verbose_name_plural = '评价'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_type_display()} {self.rating}星'


class Notification(models.Model):
    """站内信：订单确认/派工/退房/结算等关键事件通知（FR-MSG-01）"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='notifications', verbose_name='接收人')
    event = models.CharField('事件代码', max_length=50)
    title = models.CharField('标题', max_length=100)
    content = models.CharField('内容', max_length=500, blank=True, default='')
    is_read = models.BooleanField('已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '站内信'
        verbose_name_plural = '站内信'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read'])]

    def __str__(self):
        return self.title
