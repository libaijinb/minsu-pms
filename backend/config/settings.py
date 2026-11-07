"""
Django settings for PMS（民宿短租管理系统）。
关键配置：
- MySQL 8（root/123456），连接失败自动降级 SQLite，保证项目零配置可跑
- DRF 全局 JWT 认证；6 个业务 app 注册
"""

from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-pms-dev-key-only-for-local-development-1234567890'
DEBUG = True
ALLOWED_HOSTS = ['*']


def _mysql_available() -> bool:
    """探测 MySQL 是否可用：连不上就降级 SQLite（简历可讲的配置降级策略）"""
    try:
        import pymysql
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root',
                               password='123456', database='pms', connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'corsheaders',
    'users',
    'listings',
    'orders',
    'services',
    'finance',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 数据库：MySQL 优先，不可用时降级 SQLite
if _mysql_available():
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'pms',
            'USER': 'root',
            'PASSWORD': '123456',
            'HOST': '127.0.0.1',
            'PORT': 3306,
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'users.User'  # 自定义用户模型（加手机号/多角色）

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = 'media/'  # 房源图片等上传文件
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF：默认 JWT 认证 + 登录态要求；注册/登录等接口单独放行 AllowAny
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
    'COERCE_DECIMAL_TO_STRING': False,  # 金额字段输出 JSON 数字而非字符串，前端免转换
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# Celery：broker 与结果后端都指向本机 Redis
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TIMEZONE = TIME_ZONE

# beat 定时任务： PMS 的四个自动化场景（支付超时/自动确认/日历补漏/月结）
CELERY_BEAT_SCHEDULE = {
    'scan-payment-timeout': {
        'task': 'orders.tasks.scan_payment_timeout',
        'schedule': 60.0,  # 每分钟扫一遍超时未支付订单
    },
    'auto-confirm-orders': {
        'task': 'orders.tasks.auto_confirm_orders',
        'schedule': 600.0,  # 每 10 分钟：24 小时未确认的订单自动确认
    },
    'backfill-calendar': {
        'task': 'listings.tasks.backfill_calendar',
        'schedule': 3600.0,  # 每小时补齐未来 365 天日历
    },
    'monthly-settlement': {
        'task': 'finance.tasks.monthly_settlement',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # 每月 1 日 02:00 月结
    },
}
