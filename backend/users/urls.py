from django.urls import path

from . import views

# 认证相关：挂在 /api/auth/ 前缀下
auth_urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('me/', views.MeView.as_view(), name='me'),
    path('password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('roles/', views.RoleListView.as_view(), name='role_list'),
]

# 用户管理：挂在 /api/users/ 前缀下（运营管理用户与角色）
user_urlpatterns = [
    path('', views.UserListView.as_view(), name='user_list'),
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='user_role_update'),
]

urlpatterns = auth_urlpatterns + user_urlpatterns
