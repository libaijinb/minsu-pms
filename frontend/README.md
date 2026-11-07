# PMS 前端（民宿短租管理系统 · 客人端 + 运营后台）

Vue 3 + Vite + Element Plus 实现的前后端分离前端，对应后端项目 `djangoprojects/pms`。

- **客人端**：现代化消费网站风格（暖珊瑚品牌色、卡片流、毛玻璃导航、价格日历）
- **运营后台**：Element Plus 效率风，按角色过滤菜单的 6 角色工作台

## 启动

```bash
npm install
npm run dev          # http://localhost:5174
```

`/api` 已代理到后端 `http://localhost:8000`，对应后端文档见 `djangoprojects/pms/README.md`。

## 演示账号（密码均为 123456）

`guest01`（客人）、`landlord01`（房东）、`operator01`（运营）、`cleaner01`（保洁）、`repairer01`（维修）、`finance01`（财务）。

## 目录

```
src/
├── api/           axios 封装（auth/listings/orders/services/finance/core）
├── stores/        Pinia
├── layouts/       GuestLayout / AdminLayout
├── components/    ListingCard / PriceCalendar
├── views/         auth / guest(首页·详情·预订·我的订单) / admin(10 页)
├── styles/        theme.css（品牌色与全局样式）
└── router/        分区路由 + 角色守卫
```
