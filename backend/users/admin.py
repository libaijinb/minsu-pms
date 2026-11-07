from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'label']
    search_fields = ['code', 'label']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """用户后台：在 Django 默认基础上展示手机号与角色"""

    list_display = ['id', 'username', 'phone', 'get_roles', 'is_staff', 'date_joined']
    list_filter = ['roles', 'is_staff']
    search_fields = ['username', 'phone']

    def get_roles(self, obj):
        return '、'.join(r.label for r in obj.roles.all())
    get_roles.short_description = '角色'
