from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Role, User
from .permissions import IsOperator
from .serializers import (ChangePasswordSerializer, LoginSerializer,
                          RegisterSerializer, RoleAssignSerializer,
                          RoleSerializer, UserSerializer)


class RegisterView(CreateAPIView):
    """POST /api/auth/register/ 注册（客人/房东自助，无需登录）"""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    """POST /api/auth/login/ 登录，返回双 token + 用户信息（含角色列表）"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class MeView(RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ 查看和修改当前登录用户资料"""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST /api/auth/password/ 修改密码，成功后直接返回新 token 前端无缝替换"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        refresh = RefreshToken.for_user(user)
        return Response({'detail': '密码修改成功',
                         'access': str(refresh.access_token), 'refresh': str(refresh)})


class RoleListView(ListAPIView):
    """GET /api/auth/roles/ 角色列表（运营分配角色用）"""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class UserListView(ListAPIView):
    """GET /api/users/ 用户列表（运营）：支持 username/phone 搜索 + role 过滤"""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = User.objects.prefetch_related('roles').all()
        role = self.request.query_params.get('role')
        keyword = self.request.query_params.get('keyword')
        if role:
            qs = qs.filter(roles__code=role)
        if keyword:
            qs = qs.filter(username__icontains=keyword) | qs.filter(phone__icontains=keyword)
        return qs.order_by('-date_joined').distinct()


class UserRoleUpdateView(APIView):
    """POST /api/users/{id}/roles/ 运营给用户分配角色（覆盖式）"""

    permission_classes = [IsOperator]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        roles = Role.objects.filter(code__in=serializer.validated_data['roles'])
        user.roles.set(roles)
        return Response(UserSerializer(user).data)
