# 🏕️ 某露营地 — 综合运营平台

> 微信小程序 + Web管理后台 + 后端API 全栈项目

某露营地是一个户外露营品牌的数字化运营平台，为露营爱好者提供营位预定、装备租赁、户外活动报名、商品购买等一站式服务，同时为运营方提供完整的后台管理能力。

---

## 📐 系统架构

```
┌────────────────────┐   ┌────────────────────┐
│   微信小程序 (C端)   │   │  Web管理后台 (B端)   │
│  TypeScript + SCSS  │   │ Vue3 + Element Plus │
└────────┬───────────┘   └────────┬───────────┘
         │                        │
         └──────────┬─────────────┘
                    │  HTTP / WebSocket
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

---

## 📁 项目结构

```
yyyl/
├── miniprogram/          # 微信小程序前端（C端 + 员工验票端）
│   ├── pages/            # 17个页面
│   ├── components/       # 4个通用组件
│   ├── utils/            # 工具函数（请求、认证、存储）
│   ├── app.ts            # 小程序入口
│   └── app.json          # 小程序配置
│
├── server/               # 后端服务（FastAPI）
│   ├── models/           # SQLAlchemy 数据模型（45张表）
│   ├── schemas/          # Pydantic 请求/响应模型
│   ├── routers/          # API 路由（11个模块，71条API）
│   ├── services/         # 业务逻辑层（7个服务）
│   ├── middleware/       # 中间件
│   ├── utils/            # 工具函数（加密、认证、微信SDK等）
│   ├── alembic/          # 数据库迁移
│   ├── main.py           # 应用入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── redis_client.py   # Redis 连接
│   └── requirements.txt  # Python 依赖
│
├── admin/                # Web管理后台前端（B端）
│   ├── src/
│   │   ├── api/          # 7个API模块
│   │   ├── views/        # 15个页面视图
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── router/       # 路由配置 + 权限守卫
│   │   ├── layout/       # 主布局
│   │   ├── types/        # TypeScript 类型定义
│   │   ├── utils/        # 工具函数
│   │   └── styles/       # 主题样式（SCSS）
│   ├── vite.config.ts    # Vite 配置
│   └── package.json      # Node.js 依赖
│
├── docs/                 # 项目文档
│   ├── architecture.md   # 技术架构设计文档 v1.1
│   └── test_report.md    # 测试与合规报告
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
| **Node.js** | >= 18.x | Web管理后台构建 |
| **npm** | >= 9.x | Node.js 包管理 |
| **Python** | >= 3.11 | 后端运行时 |
| **pip** | >= 23.x | Python 包管理 |
| **PostgreSQL** | >= 15.x | 主数据库 |
| **Redis** | >= 7.x | 缓存 / 消息队列 / 会话 |
| **微信开发者工具** | 最新稳定版 | 小程序开发调试 |

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

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**启动成功后**：
- API 文档（Swagger UI）：http://localhost:8000/docs
- API 文档（ReDoc）：http://localhost:8000/redoc
- 健康检查：http://localhost:8000/health

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

### 5. 微信小程序

```bash
# 1. 下载并安装「微信开发者工具」
#    https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html

# 2. 打开微信开发者工具，选择「导入项目」

# 3. 项目目录选择：yyyl/miniprogram/

# 4. AppID 填写你的小程序 AppID（或使用测试号）

# 5. 点击「确定」即可预览
```

#### 小程序技术栈

| 技术 | 说明 |
|------|------|
| TypeScript | 主开发语言 |
| SCSS | 样式预处理 |
| 微信基础库 | >= 3.3.4 |
| 编译插件 | typescript + sass |

#### 小程序配置

在 `miniprogram/utils/request.ts` 中修改后端 API 地址：

```typescript
const BASE_URL = 'http://localhost:8000/api/v1'  // 开发环境
// const BASE_URL = 'https://your-domain.com/api/v1'  // 生产环境
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

# ---- 微信小程序配置 ----
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

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

---

## 🔌 API 模块概览

后端共 **11个路由模块**，**71+ 条 API**：

| 模块 | 前缀 | 说明 |
|------|------|------|
| `auth` | `/api/v1/auth` | 认证（微信登录、管理员登录、Token刷新） |
| `products` | `/api/v1/products` | 商品管理（CRUD、上下架、价格日历） |
| `orders` | `/api/v1/orders` | 订单管理（下单、支付、退票、验票） |
| `cart` | `/api/v1/cart` | 购物车 |
| `members` | `/api/v1/members` | 会员管理（年卡、次数卡、积分） |
| `users` | `/api/v1/users` | 用户信息管理 |
| `tickets` | `/api/v1/tickets` | 电子票（生成、扫码验票） |
| `finance` | `/api/v1/finance` | 财务管理（账户、交易、提现） |
| `admin` | `/api/v1/admin` | 管理后台专用（Dashboard、员工、日志、设置） |
| `content` | `/api/v1/content` | 内容管理（FAQ、页面配置） |
| `notifications` | `/api/v1/notifications` | 消息通知管理 |

---

## 📱 小程序页面一览

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `pages/index` | Banner + 推荐商品 + 分类入口 |
| 分类 | `pages/category` | 商品分类浏览 |
| 购物车 | `pages/cart` | 商品管理 + 结算 |
| 订单列表 | `pages/order` | 全部/待付款/待使用/已完成 |
| 我的 | `pages/mine` | 个人中心 + 功能入口 |
| 商品详情 | `pages/product-detail` | 图文介绍 + SKU选择 + 日历 |
| 订单确认 | `pages/order-confirm` | 出行人填写 + 支付 |
| 支付 | `pages/payment` | 支付页面（模拟支付） |
| 支付结果 | `pages/payment-result` | 支付成功/失败 |
| 订单详情 | `pages/order-detail` | 订单信息 + 操作（退票/验票） |
| 电子票 | `pages/ticket` | 二维码展示 + 使用记录 |
| 会员中心 | `pages/member` | 年卡/次数卡/积分 |
| 个人信息 | `pages/profile` | 头像/昵称/手机号 |
| 身份管理 | `pages/identity` | 出行人身份信息（AES加密） |
| 地址管理 | `pages/address` | 收货地址 CRUD |
| 员工验票 | `pages/staff` | 扫码验票（员工端） |
| 客服 | `pages/customer-service` | 在线客服 |

---

## 🖥️ 管理后台页面一览

| 页面 | 说明 |
|------|------|
| 登录 | 账号密码登录 + 微信扫码预留 |
| Dashboard | 实时数据卡片 + 趋势图 + 销售排行 + 品类分布 + 会员数据 + 财务概览 |
| 营地日历 | 按月查看所有商品库存/价格/状态矩阵 |
| 商品管理 | 商品列表 + 新增/编辑（CRUD/上下架/定价） |
| 订单管理 | 订单列表 + 详情 + 退款审批 |
| 会员管理 | 会员列表/详情/积分调整 |
| 年卡管理 | 年卡配置 + 积分兑换活动 |
| 次数卡管理 | 次数卡配置 + 激活码批量生成 |
| 财务管理 | 概览卡片 + 交易流水 |
| 数据统计 | 销售报表（ECharts 图表）+ 导出 |
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

## 📋 技术栈总结

| 层级 | 技术 |
|------|------|
| **小程序前端** | 微信原生 + TypeScript + SCSS |
| **管理后台前端** | Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts |
| **后端 API** | Python 3.11 + FastAPI + Uvicorn (ASGI) |
| **ORM** | SQLAlchemy 2.0 (Async) |
| **数据库** | PostgreSQL 15 |
| **缓存/队列** | Redis 7 |
| **异步任务** | Celery + Redis Broker |
| **数据库迁移** | Alembic |
| **API 文档** | Swagger UI / ReDoc（自动生成） |

---

## 📄 项目文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 产品需求文档 | `prd/yyyl_prd.md` | PRD v1.4（评审通过 9.6/10） |
| 技术架构文档 | `docs/architecture.md` | 架构设计 v1.1（评审通过 9.3/10） |
| 测试合规报告 | `docs/test_report.md` | 综合评分 8.5/10 |

---

## 📝 License

Private — All rights reserved.
