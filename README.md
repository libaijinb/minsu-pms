# 民宿短租 PMS · 房源 / 订单 / 结算一体化系统

前后端分离的民宿短租管理系统，覆盖房源、订单、结算三条主线，分**客人端**与**运营后台**两套界面。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Django + Django REST Framework |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios |
| 数据库 | SQLite（开发环境） |

## 业务模块

后端按 6 个业务域拆分：

| 模块 | 职责 |
|---|---|
| `users` | 用户、角色与权限 |
| `listings` | 房源信息与日历库存 |
| `orders` | 订单创建与状态流转 |
| `services` | 附加服务与清洁派工 |
| `finance` | 结算与月结入账 |
| `core` | 公共基类、权限组件等基础设施 |

## 两个核心设计

### 1. 防超售：条件更新 + 唯一约束

房源与日期的占用记录上加**唯一约束**，下单时走**条件更新**而不是「先查再插」，
把并发判断交给数据库而不是应用层。并发抢同一晚时只有一单能成功。

### 2. 订单状态机驱动副作用

订单状态以**状态转移表**定义合法流转，状态变更时触发占房、清洁派工、月结入账等动作，
避免状态判断散落在各处 `if/else` 中。

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 目录结构

```
backend/     DRF 接口层（6 个业务域）
frontend/    Vue 3 客人端与运营后台
```
