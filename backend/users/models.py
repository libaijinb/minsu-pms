from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    """
    角色：房东/运营/客人/保洁/维修/财务。
    用户可同时拥有多个角色，权限取并集（BR-USR-03），
    例如一个人既当房东又当客人。
    """

    code = models.CharField('角色代码', max_length=20, unique=True)  # landlord/operator/guest/cleaner/repairer/finance
    label = models.CharField('角色名称', max_length=20)

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'

    def __str__(self):
        return self.label


class User(AbstractUser):
    """自定义用户：Django 内置字段（username/password/email）+ 手机号、头像、多角色"""

    phone = models.CharField('手机号', max_length=11, blank=True, default='')
    avatar = models.URLField('头像', blank=True, default='')
    roles = models.ManyToManyField(Role, verbose_name='角色', related_name='users', blank=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def has_role(self, code):
        """判断用户是否拥有某角色"""
        return self.roles.filter(code=code).exists()
