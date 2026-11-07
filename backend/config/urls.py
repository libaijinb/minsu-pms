"""
config URL Configuration：
- /admin/                Django 后台（演示数据管理）
- /api/auth/             认证（注册/登录/我的资料/改密码/token刷新）
- /api/                  业务接口（各 app 的 urls.py）
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from users.urls import auth_urlpatterns, user_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include(auth_urlpatterns)),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/', include(user_urlpatterns)),
    path('api/', include('listings.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('services.urls')),
    path('api/', include('finance.urls')),
    path('api/', include('core.urls')),
]
