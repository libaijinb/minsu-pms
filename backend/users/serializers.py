from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Role, User


class RegisterSerializer(serializers.ModelSerializer):
    """注册：客人/房东自助注册，密码两次确认，注册即授予所选角色"""

    REGISTERABLE_ROLES = ['guest', 'landlord']  # 保洁/维修/财务等角色只能由运营分配

    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, label='确认密码')
    role = serializers.ChoiceField(choices=[('guest', '客人'), ('landlord', '房东')], default='guest', write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'password2', 'phone', 'email', 'role']
        extra_kwargs = {
            'username': {'validators': [], 'error_messages': {'required': '用户名不能为空'}},
            'phone': {'required': False},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('该用户名已被注册')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': '两次输入的密码不一致'})
        return attrs

    def create(self, validated_data):
        role_code = validated_data.pop('role')
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        role, _ = Role.objects.get_or_create(code=role_code, defaults={'label': dict(self.fields['role'].choices)[role_code]})
        user.roles.add(role)
        return user


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code', 'label']


class UserSerializer(serializers.ModelSerializer):
    """用户信息：roles 输出 [{code, label}]，前端按 code 判断界面"""

    roles = RoleSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'phone', 'email', 'avatar', 'roles', 'date_joined']
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {'username': {'error_messages': {'unique': '该用户名已被占用'}}}


class LoginSerializer(serializers.Serializer):
    """登录校验：authenticate 验证，失败统一提示"""

    username = serializers.CharField(label='用户名')
    password = serializers.CharField(write_only=True, label='密码')

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if user is None:
            raise serializers.ValidationError('用户名或密码错误')
        if not user.is_active:
            raise serializers.ValidationError('账号已被禁用')
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码：验原密码 + 两次新密码一致"""

    old_password = serializers.CharField(write_only=True, label='原密码')
    new_password = serializers.CharField(write_only=True, min_length=6, label='新密码')
    new_password2 = serializers.CharField(write_only=True, label='确认新密码')

    def validate_old_password(self, value):
        if not self.context['user'].check_password(value):
            raise serializers.ValidationError('原密码错误')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password2': '两次输入的新密码不一致'})
        return attrs


class RoleAssignSerializer(serializers.Serializer):
    """运营给用户分配角色：整体覆盖式赋值"""

    roles = serializers.ListField(child=serializers.CharField(), allow_empty=False, label='角色代码列表')

    def validate_roles(self, value):
        valid = set(Role.objects.values_list('code', flat=True))
        invalid = set(value) - valid
        if invalid:
            raise serializers.ValidationError(f'无效角色代码: {",".join(invalid)}')
        return value
