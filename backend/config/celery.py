"""
Celery 应用配置：
- broker/backend 用本机 Redis（6379 库 0）
- beat 定时任务在 settings.CELERY_BEAT_SCHEDULE 声明（支付超时扫描、自动确认、日历补漏、月结）
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('pms')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()  # 自动发现各 app 下的 tasks.py
