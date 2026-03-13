# 🏕️ 一月一露 — 多营地综合运营平台

> uni-app 跨平台小程序 + Web管理后台 + 后端API 全栈项目

一月一露是一个户外露营品牌的数字化运营平台，支持**多营地独立运营**（西郊林场 / 大聋谷），同一套代码通过构建时配置生成不同营地的小程序。为露营爱好者提供营位预定、装备租赁、户外活动报名、商品购买等一站式服务，同时为运营方提供完整的后台管理能力。

---

## 📐 系统架构

```
┌─────────────────────────────────────────────┐
│        uni-app 跨平台小程序 (C端)              │
│      Vue3 + TypeScript + Pinia + SCSS        │
│                                              │
│  ┌──────────────┐    ┌──────────────┐        │
│  │ 🌲 西郊林场   │    │  ⛺ 大聋谷    │  ...   │
│  │  site_id=1   │    │  site_id=2   │        │
│  │  绿色主题     │    │  蓝色主题     │        │
│  └──────────────┘    └──────────────┘        │
│     微信小程序 / H5 / 抖音小程序                │
└────────────┬────────────────────────────────┘
             │
             │  ┌────────────────────┐
             │  │  Web管理后台 (B端)   │
             │  │ Vue3 + Element Plus │
             │  └────────┬───────────┘
             │           │
             └─────┬─────┘
                   │  HTTP / WebSocket
                   │  X-Site-Id 请求头（营地隔离）
             ┌─────▼─────┐
             │   Nginx    │
             │ 反向代理    │
             └─────┬─────┘
                   │
             ┌─────▼─────┐
             │  FastAPI   │    ┌──────────┐
             │  Python    │◄───┤  Celery  │
             │  Uvicorn   │    │  Worker   │
             └──┬─────┬──┘    └──────────┘
                │     │
         ┌──────▼┐   ┌▼──────┐
         │ Postgres│   │ Redis │
         │  数据库  │   │ 缓存   │
         └────────┘   └───────┘
```

### 多营地架构

| 营地 | site_id | 小程序代号 | 主题色 |
|------|---------|-----------|--------|
| 一月一露·西郊林场 | 1 | `xijiao` | 🌲 森林绿 `#2E7D32` |
| 一月一露·大聋谷 | 2 | `dalonggu` | ⛺ 深蓝 `#1565C0` |

- **前端**：同一套代码，通过 `VITE_SITE_CODE` 环境变量在构建时切换品牌名、主题色、Slogan 等
- **后端**：所有 API 通过 `X-Site-Id` 请求头实现数据隔离，每个营地看到各自的商品、订单、用户、报表数据

---

## 📁 项目结构

```
yyyl/
├── uni-app/                # 跨平台小程序前端（C端 + 员工验票端）
│   ├── src/
│   │   ├── pages/          # 17个页面（Vue3 SFC）
│   │   ├── components/     # 通用组件
│   │   ├── config/         # 营地配置（多营地品牌/主题/Slogan）
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── types/          # TypeScript 类型定义
│   │   ├── utils/          # 工具函数（请求、认证、存储）
│   │   ├── App.vue         # 应用入口
│   │   └── pages.json      # 页面路由配置
│   ├── dist/               # 构建产物
│   ├── vite.config.ts      # Vite 配置 + uni-app 插件
│   └── package.json        # Node.js 依赖
│
├── server/               # 后端服务（FastAPI）
│   ├── models/           # SQLAlchemy 数据模型（45张表）
│   ├── schemas/          # Pydantic 请求/响应模型
│   ├── routers/          # API 路由（13个模块，106+ 条API）
│   ├── services/         # 业务逻辑层（7个服务）
│   ├── tasks/            # Celery 异步任务（23个定时任务）
│   ├── middleware/       # 中间件
│   ├── utils/            # 工具函数（加密、认证、微信SDK等）
│   ├── images/           # 商品占位图片（静态文件服务）
│   ├── alembic/          # 数据库迁移
│   ├── main.py           # 应用入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── redis_client.py   # Redis 连接
│   ├── celery_app.py     # Celery 实例初始化
│   ├── celery_config.py  # Celery Beat 定时任务调度
│   ├── seed_admin.py     # 管理员种子数据脚本
│   ├── seed_products.py  # 商品种子数据脚本（18件商品+SKU+库存+定价）
│   └── requirements.txt  # Python 依赖
│
├── admin/                # Web管理后台前端（B端）
│   ├── src/
│   │   ├── api/          # 8个API模块
│   │   ├── views/        # 17个页面视图
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── router/       # 路由配置 + 权限守卫
│   │   ├── layout/       # 主布局
│   │   ├── config/       # 品牌配置
│   │   ├── types/        # TypeScript 类型定义
│   │   ├── utils/        # 工具函数
│   │   └── styles/       # 主题样式（SCSS）
│   ├── vite.config.ts    # Vite 配置
│   └── package.json      # Node.js 依赖
│
├── nginx/                # Nginx 网关配置
│   ├── nginx.conf        # 反向代理 + 多级限流（秒杀/登录/普通API）
│   └── Dockerfile        # Nginx 镜像
│
├── k8s/                  # K8s 部署清单（腾讯云 TKE）
│   ├── namespace.yaml    # 命名空间
│   ├── configmap.yaml    # 非敏感配置
│   ├── secret.yaml       # 敏感配置模板（⚠️ 不提交真实值）
│   ├── api-deployment.yaml   # FastAPI Deployment + Service
│   ├── api-hpa.yaml      # 自动水平扩缩容（秒杀扩容 2→8 Pod）
│   ├── worker-deployment.yaml # Celery Worker
│   ├── beat-deployment.yaml   # Celery Beat（单副本）
│   ├── admin-deployment.yaml  # 管理后台 + Service
│   └── ingress.yaml      # Ingress（SSL + 限流）
│
├── docker-compose.yml    # Docker Compose 部署配置
│
├── docs/                 # 项目文档
│   ├── architecture.md   # 技术架构设计文档 v1.1
│   ├── test_report.md    # 测试与合规报告
│   └── test_cases.md     # 完整测试用例（203条）
│
├── prd/                  # 产品文档
│   └── yyyl_prd.md       # 产品需求文档 v1.4
│
└── needs/                # 原始需求资料
```

---

## 🛠️ 环境要求

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| **Node.js** | >= 18.x | uni-app 构建 + Web管理后台构建 |
| **npm** | >= 9.x | Node.js 包管理 |
| **Python** | >= 3.11 | 后端运行时 |
| **pip** | >= 23.x | Python 包管理 |
| **PostgreSQL** | >= 15.x | 主数据库 |
| **Redis** | >= 7.x | 缓存 / 消息队列 / 会话 |
| **微信开发者工具** | 最新稳定版 | 小程序导入构建产物、预览调试 |

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repo-url> yyyl
cd yyyl
```

### 2. 启动基础设施（PostgreSQL + Redis）

如果你本地没有安装 PostgreSQL 和 Redis，推荐使用 Docker：

```bash
# 使用 Docker 启动 PostgreSQL 和 Redis
docker run -d --name yyyl-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=yyyl \
  -p 5432:5432 \
  postgres:15

docker run -d --name yyyl-redis \
  -p 6379:6379 \
  redis:7-alpine
```

或者使用 docker-compose（如已有对应服务可跳过）：

```bash
# 也可以手动安装：
# macOS:
brew install postgresql@15 redis
brew services start postgresql@15
brew services start redis
createdb yyyl
```

---

### 3. 后端服务（FastAPI）

```bash
cd server

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入实际配置（见下方环境变量说明）

# 数据库迁移
alembic upgrade head

# 初始化管理员账号（首次运行时执行）
python seed_admin.py

# 初始化商品种子数据（可选，提供示例商品）
python seed_products.py

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**启动成功后**：
- API 文档（Swagger UI）：http://localhost:8000/docs
- API 文档（ReDoc）：http://localhost:8000/redoc
- 健康检查：http://localhost:8000/health
- **默认管理员账号**：`admin` / `admin123456`（⚠️ 生产环境必须修改！）

#### 后端 Python 依赖清单

| 包名 | 版本 | 用途 |
|------|------|------|
| fastapi | 0.115.0 | Web 框架 |
| uvicorn[standard] | 0.30.0 | ASGI 服务器 |
| sqlalchemy[asyncio] | 2.0.35 | ORM + 异步数据库 |
| asyncpg | 0.30.0 | PostgreSQL 异步驱动 |
| alembic | 1.14.0 | 数据库迁移 |
| pydantic | 2.10.0 | 数据验证 |
| pydantic-settings | 2.6.0 | 配置管理 |
| redis[hiredis] | 5.2.0 | Redis 客户端 |
| python-jose[cryptography] | 3.3.0 | JWT Token |
| bcrypt | 4.2.0 | 密码哈希 |
| httpx | 0.27.0 | HTTP 客户端（调微信API） |
| python-multipart | 0.0.12 | 文件上传 |
| celery[redis] | 5.4.0 | 异步任务队列 |
| bleach | 6.2.0 | HTML 清洗（XSS 防护） |
| cryptography | 43.0.0 | AES 加密（敏感数据） |
| python-dotenv | 1.0.1 | 环境变量加载 |

---

### 4. Web 管理后台（Vue3）

```bash
cd admin

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

**启动成功后**：
- 管理后台：http://localhost:3000
- API 请求自动代理到 http://localhost:8000（已在 vite.config.ts 中配置）

#### 其他命令

```bash
# 生产构建
npm run build

# 预览构建产物
npm run preview
```

#### 管理后台核心依赖

| 包名 | 用途 |
|------|------|
| vue 3.5 | 前端框架 |
| element-plus 2.13 | UI 组件库 |
| vue-router 4.6 | 路由管理 |
| pinia 3.0 | 状态管理 |
| axios 1.13 | HTTP 请求 |
| echarts 6.0 | 数据可视化图表 |
| dayjs 1.11 | 日期处理 |
| @vueuse/core 14 | Vue 组合式工具集 |
| dompurify 3.3 | XSS 防护 |
| nprogress 0.2 | 页面加载进度条 |
| sass 1.98 | CSS 预处理器 |
| unplugin-auto-import | Element Plus 自动导入 |
| unplugin-vue-components | 组件自动注册 |

---

### 5. uni-app 小程序（跨平台）

```bash
cd uni-app

# 安装依赖（npm >= 11 需要加 --force，@dcloudio 依赖树存在兼容性问题）
npm install --force

# ---- 开发模式（HMR 热更新）----
# 微信小程序 - 西郊林场
npm run dev:wx:xijiao

# 微信小程序 - 大聋谷
npm run dev:wx:dalonggu

# H5 网页版
npm run dev:h5:xijiao

# ---- 生产构建 ----
# 微信小程序 - 西郊林场
npm run build:wx:xijiao

# 微信小程序 - 大聋谷
npm run build:wx:dalonggu

# TypeScript 类型检查
npm run type-check
```

**构建产物**：
- 微信小程序：`dist/build/mp-weixin/` → 导入微信开发者工具即可预览
- H5 网页版：`dist/build/h5/`

#### 小程序技术栈

| 技术 | 说明 |
|------|------|
| **uni-app** | 跨平台框架（Vue3 模式） |
| **Vue 3** | 组合式 API (Composition API) |
| **TypeScript** | 主开发语言 + 严格模式 |
| **Pinia** | 状态管理 |
| **SCSS** | 样式预处理 |
| **Vite** | 构建工具 |

#### 支持平台

| 平台 | 构建命令 | 状态 |
|------|---------|------|
| 微信小程序 | `npm run build:wx:{营地}` | ✅ 已验证 |
| H5 网页版 | `npm run build:h5:{营地}` | ✅ 已配置 |
| 抖音小程序 | `npm run build:tt:{营地}` | 📌 已预留 |

#### 营地配置

在 `uni-app/src/config/sites.ts` 中定义各营地的品牌信息：

```typescript
// 构建时通过 VITE_SITE_CODE 环境变量选择营地
// .env.xijiao → VITE_SITE_CODE=xijiao
// .env.dalonggu → VITE_SITE_CODE=dalonggu
```

API 地址在 `uni-app/src/utils/request.ts` 中通过环境变量配置：

```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
```

> ⚠️ 微信开发者工具中需关闭「不校验合法域名」选项才能请求 localhost。

---

## ⚙️ 环境变量配置

后端环境变量在 `server/.env` 中配置，模板文件为 `server/.env.example`：

```bash
# ---- 应用配置 ----
APP_NAME=某露营地
APP_ENV=development          # development | production
DEBUG=true                   # 生产环境设为 false

# ---- 数据库配置 ----
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/yyyl
DATABASE_POOL_SIZE=20        # 连接池大小
DATABASE_MAX_OVERFLOW=10     # 最大溢出连接数

# ---- Redis配置 ----
REDIS_URL=redis://localhost:6379/0

# ---- JWT配置 ----
JWT_SECRET_KEY=your-jwt-secret-key    # ⚠️ 生产环境必须修改！
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # Token有效期（分钟）

# ---- 微信小程序配置（多营地 JSON 格式）----
WECHAT_APPS=[{"site_id":1,"app_id":"your_xijiao_appid","app_secret":"your_xijiao_secret"},{"site_id":2,"app_id":"your_dalonggu_appid","app_secret":"your_dalonggu_secret"}]

# ---- 微信支付配置（预留） ----
WECHAT_MCH_ID=your_mch_id
WECHAT_API_KEY=your_api_key
WECHAT_CERT_PATH=/path/to/apiclient_cert.pem
WECHAT_KEY_PATH=/path/to/apiclient_key.pem
WECHAT_NOTIFY_URL=https://your-domain.com/api/v1/payment/notify

# ---- AES加密配置 ----
AES_ENCRYPTION_KEY=your-32-byte-aes-key-here    # ⚠️ 生产环境必须修改！

# ---- CORS配置 ----
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

---

## 🧪 开发常用命令速查

### 后端

```bash
cd server
source venv/bin/activate

# 启动开发服务器（热重载）
uvicorn main:app --reload --port 8000

# 创建数据库迁移
alembic revision --autogenerate -m "描述信息"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 启动 Celery Worker（异步任务）
celery -A celery_app worker --loglevel=info

# 启动 Celery Beat（定时任务）
celery -A celery_app beat --loglevel=info
```

### 管理后台

```bash
cd admin

# 开发模式
npm run dev

# 构建
npm run build

# 预览构建产物
npm run preview
```

### uni-app 小程序

```bash
cd uni-app

# 开发模式（微信小程序 - 西郊林场）
npm run dev:wx:xijiao

# 开发模式（微信小程序 - 大聋谷）
npm run dev:wx:dalonggu

# 生产构建
npm run build:wx:xijiao
npm run build:wx:dalonggu

# TypeScript 类型检查
npm run type-check
```

---

## 🔌 API 模块概览

后端共 **13个路由模块**，**106+ 条 API**：

| 模块 | 前缀 | 说明 |
|------|------|------|
| `auth` | `/api/v1/auth` | 认证（微信登录、手机号登录、管理员登录、Token刷新） |
| `products` | `/api/v1/products` | 商品管理（CRUD、上下架、价格日历） |
| `campsites` | `/api/v1/admin/campsites` | 营位管理（CRUD、库存批量开放、定价规则、统计） |
| `orders` | `/api/v1/orders` | 订单管理（下单、支付、退票、验票） |
| `cart` | `/api/v1/cart` | 购物车（添加、更新、删除、结算拆单） |
| `members` | `/api/v1/members` | 会员管理（年卡、次数卡、积分） |
| `users` | `/api/v1/users` | 用户信息管理 |
| `tickets` | `/api/v1/tickets` | 电子票（生成、扫码验票） |
| `finance` | `/api/v1/finance` | 财务管理（账户、交易、提现） |
| `admin` | `/api/v1/admin` | 管理后台专用（Dashboard、员工、日志、设置、日历等） |
| `content` | `/api/v1/content` | 内容管理（FAQ、页面配置、免责声明） |
| `notifications` | `/api/v1/notifications` | 消息通知管理 |
| `reports` | `/api/v1/admin/reports` | 数据报表（销售/用户/商品报表、导出） |

---

## 📱 小程序页面一览（uni-app）

| 页面 | 路径 | 说明 | API 状态 |
|------|------|------|---------|
| 首页 | `pages/index` | Banner + 推荐商品 + 分类入口 | ✅ 已接入 |
| 分类 | `pages/category` | 商品分类浏览 + 搜索 | ✅ 已接入 |
| 购物车 | `pages/cart` | 商品管理 + 结算 | ✅ 已接入 |
| 订单列表 | `pages/order` | 全部/待付款/待使用/已完成 | ✅ 已接入 |
| 我的 | `pages/mine` | 个人中心 + 功能入口 | ✅ 已接入 |
| 商品详情 | `pages/product-detail` | 图文介绍 + SKU选择 + 日历 | ✅ 已接入 |
| 订单确认 | `pages/order-confirm` | 出行人填写 + 支付 | ✅ 已接入 |
| 支付 | `pages/payment` | 模拟支付（成功/失败） | ✅ 已接入 |
| 支付结果 | `pages/payment-result` | 支付成功/失败展示 | 纯展示 |
| 订单详情 | `pages/order-detail` | 订单信息 + 退票操作 | ✅ 已接入 |
| 电子票 | `pages/ticket` | 二维码展示 + QR刷新 | ✅ 已接入 |
| 会员中心 | `pages/member` | 年卡/次数卡/积分 | ✅ 已接入 |
| 个人信息 | `pages/profile` | 头像/昵称修改 | ✅ 已接入 |
| 身份管理 | `pages/identity` | 出行人身份信息（AES加密） | ✅ 已接入 |
| 地址管理 | `pages/address` | 收货地址 CRUD | ✅ 已接入 |
| 员工验票 | `pages/staff` | 扫码验票（员工端） | ✅ 已接入 |
| 客服 | `pages/customer-service` | FAQ + 在线客服 | ✅ 已接入 |

---

## 🖥️ 管理后台页面一览

| 页面 | 说明 |
|------|------|
| 登录 | 账号密码登录 + 微信扫码预留 |
| Dashboard | 实时数据卡片 + 趋势图 + 销售排行 + 品类分布 + 会员数据 + 财务概览 |
| 营地日历 | 按月查看所有营位库存/价格/状态矩阵（月份导航 + 今天标记 + 周末区分） |
| 营位管理 | 营位列表（统计概览 + 属性筛选 + 7天库存概况）+ 新增/编辑 |
| 商品管理 | 商品列表 + 新增/编辑（CRUD/上下架/定价） |
| 订单管理 | 订单列表 + 详情 + 退款审批 |
| 会员管理 | 会员列表/详情/积分调整 |
| 年卡管理 | 年卡配置 + 积分兑换活动 |
| 次数卡管理 | 次数卡配置 + 激活码批量生成 |
| 财务管理 | 概览卡片 + 交易流水 |
| 数据统计 | 销售报表（ECharts 图表）+ 用户分析 + 商品排行 + 导出 |
| FAQ管理 | 分类 + 条目 CRUD |
| 页面编辑 | JSON 配置编辑器 |
| 消息管理 | 模板开关 + 发送记录 + 统计 |
| 员工管理 | CRUD + 角色分配 |
| 系统设置 | 基本/退票规则/客服/免责声明 |
| 操作日志 | 查询 + 详情（变更前后值） |

---

## 🔐 安全机制

- **认证**：JWT 双 Token（Access 2h + Refresh 7d）
- **密码**：bcrypt 哈希存储
- **敏感数据**：AES-256-CBC 加密（身份证号等）
- **XSS 防护**：bleach HTML 清洗 + DOMPurify（前端）
- **CSRF 防护**：X-Request-Token 请求头校验
- **SQL 注入**：SQLAlchemy ORM 参数化查询
- **CORS**：白名单域名控制
- **权限控制**：基于角色的访问控制（super_admin / admin / operator / viewer）

---

## 🎨 品牌 & 营地配置

项目支持多营地独立品牌，同一套代码构建不同营地的应用：

| 文件 | 说明 |
|------|------|
| `uni-app/src/config/sites.ts` | 营地品牌定义（名称、Slogan、主题色、联系方式、坐标等） |
| `uni-app/.env.xijiao` | 西郊林场构建环境变量 |
| `uni-app/.env.dalonggu` | 大聋谷构建环境变量 |
| `admin/src/config/brand.ts` | 管理后台品牌名、描述 |
| `server/.env` → `APP_NAME` | 后端应用名称 |
| `admin/index.html` | 管理后台 HTML 标题 |

新增营地只需：
1. 在 `sites.ts` 中添加营地配置
2. 新增 `.env.{code}` 环境变量文件
3. 在 `package.json` 中添加对应的构建脚本
4. 后端 `middleware/site.py` 中允许新的 site_id

---

## 📋 技术栈总结

| 层级 | 技术 |
|------|------|
| **小程序前端** | uni-app + Vue 3 + TypeScript + Pinia + Vite + SCSS |
| **管理后台前端** | Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts |
| **后端 API** | Python 3.11 + FastAPI + Uvicorn (ASGI) |
| **ORM** | SQLAlchemy 2.0 (Async) |
| **数据库** | PostgreSQL 15 |
| **缓存/队列** | Redis 7 |
| **异步任务** | Celery + Redis Broker（23个定时任务） |
| **数据库迁移** | Alembic |
| **API 文档** | Swagger UI / ReDoc（自动生成） |
| **多营地隔离** | X-Site-Id 请求头 + 全链路 site_id 过滤 |

---

## 🐳 Docker & K8s 部署

### 部署策略分层

| 环境 | 方式 | 说明 |
|------|------|------|
| **开发/测试** | 本地直接启动 | 各服务独立运行，简单直接 |
| **集成测试** | `docker-compose up` | 一键拉起全套，验证服务间协作 |
| **线上生产** | 腾讯云 TKE (K8s) | HPA 自动扩缩容，秒杀场景弹性伸缩 |

### 本地开发（推荐方式）

各服务独立启动，便于调试：

```bash
# 1. 基础设施（PG + Redis）— 本地安装或 Docker
docker run -d --name yyyl-postgres -e POSTGRES_DB=yyyl -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15
docker run -d --name yyyl-redis -p 6379:6379 redis:7-alpine

# 2. 后端 API
cd server && source venv/bin/activate
alembic upgrade head          # 数据库迁移
python seed_admin.py          # 初始化管理员账号（首次）
python seed_products.py       # 初始化商品数据（首次，可选）
uvicorn main:app --reload --port 8000

# 3. Celery Worker（新终端）
cd server && source venv/bin/activate
celery -A celery_app worker --loglevel=info

# 4. Celery Beat（新终端）
cd server && source venv/bin/activate
celery -A celery_app beat --loglevel=info

# 5. 管理后台（新终端）
cd admin && npm run dev

# 6. uni-app 小程序（新终端）
cd uni-app && npm install --force
npm run dev:wx:xijiao     # 或 dev:wx:dalonggu
# 构建产物在 dist/dev/mp-weixin/，用微信开发者工具导入
```

### Docker Compose 部署

适合服务器上快速部署或集成测试：

```bash
# 先在 server/.env 中配置好环境变量
# 然后设置数据库密码
export DB_PASSWORD=your_secure_password

# 构建并启动全部服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看 API 日志
docker-compose logs -f api

# 停止全部
docker-compose down
```

### 腾讯云 TKE (K8s) 部署

线上生产环境使用 K8s，支持秒杀场景自动扩容：

```bash
# 1. 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 2. 创建配置和密钥（⚠️ 修改 secret.yaml 中的真实值）
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 3. 部署服务
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-hpa.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/beat-deployment.yaml
kubectl apply -f k8s/admin-deployment.yaml

# 4. 配置 Ingress（需先配置域名和 TLS 证书）
kubectl apply -f k8s/ingress.yaml

# 查看 Pod 状态
kubectl get pods -n yyyl

# 查看 HPA 扩缩容状态
kubectl get hpa -n yyyl
```

#### 秒杀扩容能力

| 指标 | 配置 |
|------|------|
| 平时副本数 | 2 Pod |
| 最大副本数 | 8 Pod |
| 扩容触发 | CPU > 60% 或 内存 > 75% |
| 扩容速度 | 30 秒内判定，一次最多加 4 Pod |
| 缩容速度 | 5 分钟稳定窗口，一次减 1 Pod |

#### 线上数据层建议

| 组件 | 推荐方案 | 理由 |
|------|---------|------|
| PostgreSQL | 腾讯云 TDSQL-C | 自动备份、主从高可用、免运维 |
| Redis | 腾讯云 Redis | 持久化、主从切换、监控告警 |
| 对象存储 | 腾讯云 COS | 图片 CDN 加速 |

> K8s 里只跑无状态服务（API、Worker、Beat、Admin），有状态的数据层交给云服务托管。

---

## 📄 项目文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 产品需求文档 | `prd/yyyl_prd.md` | PRD v1.4（评审通过 9.6/10） |
| 技术架构文档 | `docs/architecture.md` | 架构设计 v1.1（评审通过 9.3/10） |
| 测试合规报告 | `docs/test_report.md` | 综合评分 8.5/10 |
| 测试用例文档 | `docs/test_cases.md` | 203 条测试用例（P0:105 / P1:84 / P2:14） |

---

## 📝 License

Private — All rights reserved.
