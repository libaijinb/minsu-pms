import pymysql

pymysql.install_as_MySQLdb()  # 让 Django 用 PyMySQL 驱动 MySQL，无需编译 mysqlclient

import MySQLdb  # noqa: E402

# Django 6 按 mysqlclient 的版本号语义检查驱动（要求 >= 2.2.1），PyMySQL 版本号语义不同，这里对齐骗过检查
MySQLdb.version_info = (2, 2, 1, 'final', 0)

from .celery import app as celery_app  # noqa: E402,F401  项目加载时即初始化 Celery 应用

__all__ = ('celery_app',)
