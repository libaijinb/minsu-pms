from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    """
    角色权限基类：要求用户拥有指定角色之一。
    超级管理员（is_superuser）直接放行，方便后台调试。
    用法：class IsOperator(HasRole): allowed = ['operator']
    """

    allowed = []

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        return user.roles.filter(code__in=self.allowed).exists()


class IsOperator(HasRole):
    allowed = ['operator']


class IsLandlord(HasRole):
    allowed = ['landlord']


class IsCleaner(HasRole):
    allowed = ['cleaner']


class IsRepairer(HasRole):
    allowed = ['repairer']


class IsFinance(HasRole):
    allowed = ['finance']


class IsGuest(HasRole):
    allowed = ['guest']


class IsLandlordOrOperator(HasRole):
    allowed = ['landlord', 'operator']
