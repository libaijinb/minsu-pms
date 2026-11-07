from django.conf import settings
from django.db import models


class CleaningTask(models.Model):
    """
    清洁任务：客人退房后自动生成（幂等：order 唯一约束，BR-CLN-04）。
    派工冲突靠 (cleaner, task_date, slot) 唯一约束物理拦截（BR-CLN-03）；
    cleaner 为 NULL（未派工）时多条不冲突，MySQL 唯一约束天然跳过 NULL，正好符合业务。
    """

    SLOT_CHOICES = [('morning', '上午'), ('afternoon', '下午')]
    STATUS_CHOICES = [
        ('pending', '待派工'), ('assigned', '已派工'), ('doing', '进行中'),
        ('reviewing', '待复核'), ('done', '已完成'),
    ]

    order = models.OneToOneField('orders.BookingOrder', on_delete=models.CASCADE,
                                 related_name='cleaning_task', verbose_name='订单')  # 一单一清，幂等键
    listing = models.ForeignKey('listings.Listing', on_delete=models.CASCADE,
                                related_name='cleaning_tasks', verbose_name='房源')
    cleaner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='cleaning_tasks', verbose_name='保洁')
    task_date = models.DateField('任务日期')
    slot = models.CharField('时段', max_length=10, choices=SLOT_CHOICES, default='morning')
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='pending')
    requirement = models.CharField('特殊要求', max_length=200, blank=True, default='')
    photos = models.JSONField('完成照片', default=list)
    assigned_at = models.DateTimeField('派工时间', null=True, blank=True)
    finished_at = models.DateTimeField('完成时间', null=True, blank=True)
    reviewed_at = models.DateTimeField('复核时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '清洁任务'
        verbose_name_plural = '清洁任务'
        unique_together = [('cleaner', 'task_date', 'slot')]  # 派工冲突防线
        ordering = ['task_date', 'slot']

    def __str__(self):
        return f'清洁 #{self.pk} {self.task_date} {self.get_slot_display()}'


class RepairTicket(models.Model):
    """
    维修工单：四类来源（客人/房东/查房定损/运营，BR-REP-02）。
    维修期间相关日期由运营锁定为「已锁定」，完工后解锁（BR-REP-03）。
    """

    SOURCE_CHOICES = [
        ('guest', '客人报修'), ('landlord', '房东报修'),
        ('inspection', '查房定损'), ('operator', '运营创建'),
    ]
    STATUS_CHOICES = [
        ('pending', '待派工'), ('assigned', '已派工'), ('doing', '处理中'),
        ('accepting', '待验收'), ('done', '已完成'), ('closed', '已关闭'),
    ]
    URGENCY_CHOICES = [('normal', '一般'), ('urgent', '紧急')]

    listing = models.ForeignKey('listings.Listing', on_delete=models.CASCADE,
                                related_name='repair_tickets', verbose_name='房源')
    order = models.ForeignKey('orders.BookingOrder', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='repair_tickets', verbose_name='关联订单')
    source = models.CharField('来源', max_length=12, choices=SOURCE_CHOICES, default='operator')
    title = models.CharField('标题', max_length=100)
    desc = models.TextField('问题描述', blank=True, default='')
    urgency = models.CharField('紧急程度', max_length=8, choices=URGENCY_CHOICES, default='normal')
    images = models.JSONField('图片', default=list)
    repairer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='repair_tickets', verbose_name='维修师傅')
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='pending')
    cost = models.DecimalField('维修费用', max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)

    class Meta:
        verbose_name = '维修工单'
        verbose_name_plural = '维修工单'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
