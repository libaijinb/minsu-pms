# 民宿短租 PMS（Property Management System）

一个面向短租/民宿场景的房源经营管理系统，覆盖 **房源上架 → 日历价格 → 预订 → 支付 → 运营确认 → 入住 → 清洁/维修 → 退房查房 → 评价 → 月结分账** 的完整业务闭环。前后端分离，含 6 类角色工作台，可作为全栈简历项目。

---

## 技术栈

**后端**
- Django 5.2 LTS（MySQL 8.0 不可用时自动降级 SQLite）
- Django REST Framework + djangorestframework-simplejwt（JWT 鉴权）
- django-filter / django-cors-headers / PyMySQL
- Celery + Redis（异步任务与定时调度）
- Pillow（图片字段）

**前端**
- Vue 3（`<script setup>` SFC）+ Vite
- Element Plus（B 端效率风）+ Pinia + vue-router@4 + axios + dayjs
- 客人端采用现代化消费网站设计（暖珊瑚品牌色、卡片流、毛玻璃导航），与 B 端后台风格分离

---

## 角色与功能

| 角色 | 账号 | 核心功能 |
|---|---|---|
| 客人 | `guest01` | 浏览/搜索房源、查看日历价、下单预订、在线支付、我的订单、评价 |
| 房东 | `landlord01` | 房源上架、日历开关房与改价、查看自己房源订单、查看分账结算 |
| 运营 | `operator01` | 房源审核、订单确认/取消、入住退房管理、清洁派工、查房定损、数据看板 |
| 保洁 | `cleaner01` | 接收清洁任务、打卡完成、上传清洁照片 |
| 维修 | `repairer01` | 接收维修工单、处理与完成 |
| 财务 | `finance01` | 月结单核对、分账记录、生成对账单 |
| 超级管理员 | `admin` / `admin123456` | Django admin 全量数据管理 |

> 全部演示账号密码均为 `123456`。

---

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- MySQL 8.0（可选，缺失则用 SQLite）+ Redis（Celery 可选）

### 1. 后端

```bash
cd djangoprojects/pms
python -m venv venv
venv\Scripts\activate            # Windows；Linux/macOS 用 source venv/bin/activate
pip install -r requirements.txt

# 数据库：默认尝试 MySQL（库名 pms，密码 123456）；连不上自动用 SQLite，无需额外配置
python manage.py migrate
python manage.py seed_data       # 生成演示数据（6 用户 / 3 房源 / 日历 / 订单 / 各角色业务数据）

python manage.py runserver 8000 --noreload
```

可选——启动异步任务与定时调度（支付超时取消、24h 自动确认、日历补漏、每月 1 号月结）：

```bash
celery -A config worker -l info
celery -A config beat -l info
```

### 2. 前端

```bash
cd vueprojects/pms
npm install
npm run dev                     # http://localhost:5174
```

前端已配置代理将 `/api` 转发到 `http://localhost:8000`。

---

## 目录结构

```
djangoprojects/pms/
├── config/                 # 项目配置（settings / urls / celery / asgi / wsgi）
├── users/                  # 多角色用户与权限
├── listings/               # 房源、日历（晚粒度库存）、价格规则
├── orders/                 # 订单、状态机、支付、入住、查房定损、押金
├── services/               # 清洁任务、维修工单
├── finance/                # 月结单、分账记录
├── core/                   # 评价、站内信、种子数据命令
└── requirements.txt

vueprojects/pms/
├── src/
│   ├── api/                # axios 封装（auth/listings/orders/services/finance/core）
│   ├── stores/             # Pinia（user）
│   ├── layouts/            # 客人端 / 后台两套布局
│   ├── components/         # ListingCard、PriceCalendar
│   ├── views/
│   │   ├── auth/           # 登录 / 注册
│   │   ├── guest/          # 首页 / 房源详情 / 预订 / 我的订单（现代化消费风）
│   │   └── admin/          # 10 个后台页面（按角色过滤菜单）
│   ├── styles/theme.css    # 品牌色与全局样式
│   └── router/index.js     # C/B 端分区 + 角色守卫
```

---

## 核心业务闭环

```
房源上架 → 日历开关房/批量改价 → 客人预订(防超售占房) → 在线支付
   → 运营确认 → 入住登记 → 自动生成清洁任务/可报修 → 退房查房(定损扣押金)
   → 客人评价 → 月度结算 → 房东分账
```

---

## 数据库设计（6 个应用 / 17 张表）

| 应用 | 主要模型 |
|---|---|
| `users` | `Role`、`User`（多角色 M2M） |
| `listings` | `Listing`、`Calendar`（唯一 `listing+date`）、`PriceRule` |
| `orders` | `BookingOrder`、`OrderStatusLog`、`Payment`、`CheckIn`、`Inspection`（含定损/押金扣减） |
| `services` | `CleaningTask`（唯一 `cleaner+date+slot`）、`RepairTicket` |
| `finance` | `Settlement`（唯一 `landlord+period`）、`PayoutRecord` |
| `core` | `Review`（双向）、`Notification` |

---

## 技术难点与实现

- **防超售**：预订时采用「条件 `UPDATE status='available'→'booked'` + 受影响行数校验」，并叠加 `(listing_id, date)` 唯一约束作为最后防线。
- **订单状态机**：以转移表驱动合法流转，状态变更触发副作用（占房/释放、生成清洁任务、月结入账等）。
- **清洁派工冲突**：`(cleaner, date, slot)` 唯一约束防止同一保洁同一时段重复派单。
- **月结分账**：`(landlord, period)` 唯一约束保证幂等；金额全程使用 `Decimal`，避免浮点误差。
- **定时调度**：Celery beat 4 个任务——支付超时取消（60s）、24h 自动确认（600s）、日历未来 60 天补漏（3600s）、每月 1 号 02:00 月结。

---

## API 概览

| 前缀 | 说明 |
|---|---|
| `/api/auth/` | 登录、注册、刷新 token、当前用户 |
| `/api/users/` | 用户与角色管理（按角色拆分端点） |
| `/api/listings/` | 房源 CRUD、日历查询/改价、批量关房 |
| `/api/orders/` | 订单状态机（创建/支付/确认/取消/入住/退房/查房定损） |
| `/api/services/` | 清洁派工、维修工单 |
| `/api/finance/` | 月结单、分账、对账单 |
| `/api/core/` | 评价、站内信、运营统计（OCC / ADR / RevPAR） |

---

## 测试与验收

- **后端 API 层**：28 项端到端验证（鉴权、房源、订单状态机、清洁、财务、统计）全部通过。
- **前端 E2E**：24 项 Playwright 流程（登录 → 找档期 → 下单 → 支付 → 运营确认 → 清洁派工 → 月结分账）全部通过。
- **视觉验收**：12 项（品牌色、组件渲染、布局、移动端自适应、角色菜单过滤）通过。

---

## 备注

- 前端房源/场景配图使用 Picsum 真实摄影外链（联网即显示真实照片）；图片加载失败时自动回退为品牌渐变占位，不会出现空白破图。如需完全离线，可将图片下载至 `public/img/` 并将种子数据中的图片路径改为本地路径。
- 演示数据通过 `python manage.py seed_data` 幂等生成，可重复执行。
