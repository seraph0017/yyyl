# 一月一露

> 多营地户外露营综合运营平台：uni-app 小程序 + Vue3 管理后台 + FastAPI 后端

一月一露（yyyl）面向户外露营品牌的数字化经营场景，覆盖营位预订、装备租赁、活动报名、商品购买、会员权益、电子票、验票、退款、财务和运营报表。项目支持多营地独立运营，同一套代码可按营地配置构建不同小程序，并通过后端 `site_id` 做全链路数据隔离。

## 项目状态

| 项目 | 当前状态 |
|------|----------|
| 生产域名 | `https://www.yyylcamp.com` |
| 线上 API | Podman 蓝绿容器运行，Nginx 反向代理 |
| 微信支付 | 代码链路已接入真实微信支付；当前商户侧收款能力受限，真实支付返回 `NO_AUTH` |
| 测试价格 | 商品、SKU、日期定价均已临时调整为 `0.01` 元，便于支付链路测试 |
| 多营地 | 西郊林场 `site_id=1`、大聋谷 `site_id=2` |
| 项目文档 | 见 [docs/project_overview.md](docs/project_overview.md) 与 [docs/architecture.md](docs/architecture.md) |

## 快速导航

- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [本地启动](#本地启动)
- [常用命令](#常用命令)
- [环境变量](#环境变量)
- [业务模块](#业务模块)
- [设计系统](#设计系统)
- [部署说明](#部署说明)
- [项目文档](#项目文档)

## 系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│ C 端：uni-app 小程序 / H5                                      │
│ Vue3 + TypeScript + Pinia + SCSS                              │
│ VITE_SITE_CODE = xijiao / dalonggu                            │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ B 端：Vue3 管理后台                                             │
│ Element Plus + Pinia + ECharts + Vite                         │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP / WebSocket
                               │ X-Site-Id 营地隔离
┌──────────────────────────────▼───────────────────────────────┐
│ FastAPI 后端                                                   │
│ Routers + Services + Schemas + SQLAlchemy Async                │
└───────────────┬─────────────────────────────┬────────────────┘
                │                             │
        ┌───────▼────────┐            ┌───────▼────────┐
        │ PostgreSQL 15  │            │ Redis 7        │
        │ 主数据 / 事务   │            │ 缓存 / 队列     │
        └────────────────┘            └───────┬────────┘
                                              │
                                      ┌───────▼────────┐
                                      │ Celery Worker  │
                                      │ 定时任务 / 异步 │
                                      └────────────────┘
```

### 多营地隔离

| 营地 | site_id | 构建代号 | 说明 |
|------|---------|----------|------|
| 一月一露·西郊林场 | `1` | `xijiao` | 当前线上审核与测试主站点 |
| 一月一露·大聋谷 | `2` | `dalonggu` | 同代码库独立品牌配置 |

- 小程序：通过 `VITE_SITE_CODE` 在构建时选择营地品牌、主题色、文案和 API 配置。
- 后端：通过 `X-Site-Id` 请求头解析当前营地，所有核心查询按 `site_id` 过滤。
- 新增营地：更新 `uni-app/src/config/sites.ts`、新增 `.env.{code}`、补构建脚本，并在后端中间件允许新的 `site_id`。

## 目录结构

```text
yyyl/
├── uni-app/                 # C 端小程序 / H5 / 员工验票端
│   ├── src/pages/           # 首页、分类、购物车、订单、支付、电子票等
│   ├── src/pages-sub/       # 分包：营地地图、互动游戏等
│   ├── src/components/      # 业务组件与通用组件
│   ├── src/config/          # 多营地品牌配置
│   ├── src/stores/          # Pinia 状态
│   └── src/utils/           # 请求、认证、存储等工具
│
├── admin/                   # B 端管理后台
│   ├── src/api/             # Axios API 模块
│   ├── src/views/           # 商品、订单、会员、财务、报表、系统设置等页面
│   ├── src/router/          # 路由与权限守卫
│   ├── src/stores/          # Pinia 状态
│   └── src/styles/          # SCSS 主题与 Element Plus 覆盖
│
├── server/                  # FastAPI 后端
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic v2 请求 / 响应模型
│   ├── routers/             # API 路由
│   ├── services/            # 业务服务层
│   ├── tasks/               # Celery 任务
│   ├── middleware/          # 认证、多营地隔离等中间件
│   ├── alembic/             # 数据库迁移
│   └── images/              # 商品与 Banner 静态图片
│
├── scripts/                 # 运维、发布、状态更新脚本
├── scripts/prod/            # 生产 Podman 蓝绿发布脚本
├── docs/                    # 架构、测试、开发与运维文档
├── prd/                     # 产品需求文档
├── needs/                   # 原始需求资料
├── nginx/                   # Nginx 配置
├── k8s/                     # TKE / Kubernetes 部署清单
└── docker-compose.yml       # 本地或集成环境编排
```

## 本地启动

### 环境要求

| 工具 | 建议版本 | 用途 |
|------|----------|------|
| Node.js | 18+ | 小程序与管理后台构建 |
| npm | 9+ | Node 包管理 |
| Python | 3.11 | 后端运行时 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存、队列、会话 |
| 微信开发者工具 | 最新稳定版 | 小程序预览和调试 |

本机后端开发推荐使用已有 conda 环境：

```bash
conda activate yyyl
```

### 1. 启动 PostgreSQL 和 Redis

```bash
docker run -d --name yyyl-postgres \
  -e POSTGRES_DB=yyyl \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15

docker run -d --name yyyl-redis \
  -p 6379:6379 \
  redis:7-alpine
```

也可以使用本机服务：

```bash
brew install postgresql@15 redis
brew services start postgresql@15
brew services start redis
createdb yyyl
```

### 2. 启动后端

```bash
cd server
conda activate yyyl
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python seed_admin.py
python seed_products.py
uvicorn main:app --reload --port 8000
```

启动后：

| 地址 | 说明 |
|------|------|
| `http://localhost:8000/docs` | Swagger API 文档 |
| `http://localhost:8000/redoc` | ReDoc API 文档 |
| `http://localhost:8000/health` | 健康检查 |

本地默认管理员：`admin` / `admin123456`。生产环境必须修改默认账号和密钥。

### 3. 启动管理后台

```bash
cd admin
npm install
npm run dev
```

- 本地地址：`http://localhost:3000`
- `/api` 默认代理到 `http://localhost:8000`

### 4. 启动小程序

```bash
cd uni-app
npm install --force

# 西郊林场
npm run dev:wx:xijiao

# 大聋谷
npm run dev:wx:dalonggu

# H5
npm run dev:h5:xijiao
```

微信小程序构建产物在 `uni-app/dist/dev/mp-weixin/` 或 `uni-app/dist/build/mp-weixin/`，导入微信开发者工具即可。

## 常用命令

### 后端

```bash
cd server
conda activate yyyl

uvicorn main:app --reload --port 8000
alembic revision --autogenerate -m "描述信息"
alembic upgrade head
alembic downgrade -1
celery -A celery_app worker --loglevel=info
celery -A celery_app beat --loglevel=info
```

### 管理后台

```bash
cd admin
npm run dev
npm run build
npm run preview
```

### 小程序

```bash
cd uni-app
npm run dev:wx:xijiao
npm run dev:wx:dalonggu
npm run build:wx:xijiao
npm run build:wx:dalonggu
npm run type-check
```

### 回归验证

```bash
cd server
/Users/nathan/miniconda3/envs/yyyl/bin/python -m unittest \
  tests/test_order_routes.py \
  tests/test_wechat_pay_service.py \
  tests/test_payment_routes.py \
  tests/test_order_schema.py \
  tests/test_order_service.py -v
```

## 环境变量

后端模板位于 `server/.env.example`，本地开发复制为 `server/.env` 后填写。

```bash
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/yyyl
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=change-me
AES_ENCRYPTION_KEY=change-me-32-byte-key

WECHAT_APPS=[{"site_id":1,"app_id":"your_xijiao_appid","app_secret":"your_xijiao_secret"},{"site_id":2,"app_id":"your_dalonggu_appid","app_secret":"your_dalonggu_secret"}]

WECHAT_MCH_ID=your_mch_id
WECHAT_API_V3_KEY=your_32_byte_api_v3_key
WECHAT_MCH_SERIAL_NO=your_merchant_api_cert_serial_no
WECHAT_CERT_PATH=/path/to/apiclient_cert.pem
WECHAT_KEY_PATH=/path/to/apiclient_key.pem
WECHAT_PLATFORM_PUBLIC_KEY_PATH=/path/to/pub_key.pem
WECHAT_PLATFORM_PUBLIC_KEY_ID=PUB_KEY_ID_xxx
WECHAT_NOTIFY_URL=https://www.yyylcamp.com/api/v1/payments/wechat/notify
WECHAT_REFUND_NOTIFY_URL=https://www.yyylcamp.com/api/v1/payments/wechat/refund-notify

CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

注意：

- 不要提交真实密钥、证书、APIv3 Key、私钥或带凭据的 DSN。
- 生产环境 `DEBUG=false`，且 JWT/AES 密钥不能使用默认值。
- 微信支付证书生产路径为 `/opt/yyyl/secure/wechat-pay`，由 Podman 容器只读挂载。

## 业务模块

### 小程序端

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `pages/index` | Banner、推荐商品、分类入口 |
| 分类 | `pages/category` | 商品分类、搜索、筛选 |
| 商品详情 | `pages/product-detail` | 图文、SKU、日期、库存 |
| 订单确认 | `pages/order-confirm` | 出行人、价格、提交订单 |
| 支付 | `pages/payment` | 后端下单获取微信支付参数，调用 `uni.requestPayment()` |
| 订单 | `pages/order` / `pages/order-detail` | 订单列表、详情、退款 |
| 电子票 | `pages/ticket` | 二维码票券、验票状态 |
| 会员 | `pages/member` | 年卡、次数卡、积分 |
| 我的 | `pages/mine` | 个人中心、地址、身份信息 |
| 员工验票 | `pages/staff` | 员工扫码核销 |

### 管理后台

| 模块 | 说明 |
|------|------|
| Dashboard | 销售、订单、会员、财务、趋势图 |
| 商品与营位 | 商品、SKU、库存、日期定价、营地日历 |
| 订单与退款 | 订单查询、详情、退款审批 |
| 会员与权益 | 会员、年卡、次数卡、积分 |
| 财务与报表 | 交易流水、提现、销售报表、导出 |
| 内容运营 | FAQ、页面配置、公告、消息模板 |
| 营地玩法 | 搭配套餐、营地地图、游戏、秒杀监控 |
| 内部管理 | 员工、权限、报销、绩效、操作日志、系统设置 |

### 后端 API

| 模块 | 前缀 | 说明 |
|------|------|------|
| Auth | `/api/v1/auth` | 登录、Token、微信身份 |
| Products | `/api/v1/products` | 商品、SKU、价格、库存 |
| Orders | `/api/v1/orders` | 下单、支付、退款、订单详情 |
| Payments | `/api/v1/payments` | 微信支付通知、退款通知 |
| Cart | `/api/v1/cart` | 购物车、结算 |
| Tickets | `/api/v1/tickets` | 电子票、扫码验票 |
| Members | `/api/v1/members` | 会员、权益、积分 |
| Admin | `/api/v1/admin` | 管理后台聚合接口 |
| Reports | `/api/v1/admin/reports` | 销售、用户、商品报表 |
| Content | `/api/v1/content` | FAQ、页面配置、免责声明 |

## 设计系统

### 小程序：野奢 Organic Luxury Outdoor

| 元素 | 设计方向 |
|------|----------|
| 色彩 | 深苔绿 `#2d4a3e`、暖铜金 `#c8a872`、暖沙背景 `#faf6f0` |
| 视觉 | 侘寂美学、户外奢华、自然材质感 |
| 组件 | 磨砂导航、渐变标题线、日期范围选择、底部弹层表单 |
| 体验 | 商品浏览、营位选择、出行人填写、支付和电子票链路尽量短 |

### 管理后台：深邃极光 Northern Lights Dashboard

| 元素 | 设计方向 |
|------|----------|
| 色彩 | 森林绿 `#3d8b5e`、铜金 `#c8a872`、暗森林侧边栏 `#141e1a` |
| 视觉 | 极光渐变、玻璃拟态卡片、工作台式信息密度 |
| 操作 | 32px 圆形图标按钮，按编辑、查看、库存、上下架、审批、删除区分颜色 |
| 主题 | CSS 变量集中管理，Element Plus 主题覆盖在 `admin/src/styles/` |

## 部署说明

### 本地集成

```bash
docker-compose up -d --build
docker-compose ps
docker-compose logs -f api
docker-compose down
```

### 生产 Podman 蓝绿部署

生产 API 优先使用 Podman 蓝绿容器，不使用 conda 直接运行 FastAPI。详细命令见 [scripts/prod/README.md](scripts/prod/README.md)。

```bash
pip install -r scripts/ops/requirements.txt

fab info
fab preflight
fab build --tag=v0.1.0
fab deploy --tag=v0.1.0
fab health
fab rollback
```

当前线上关键点：

- Nginx 站点配置：`/www/server/panel/vhost/nginx/ttt.conf`
- 蓝绿容器：`yyyl-api-blue` / `yyyl-api-green`
- 默认端口：`8001` / `8002`
- 微信支付证书目录：`/opt/yyyl/secure/wechat-pay`
- 数据层过渡状态：PostgreSQL/Redis 仍在 Docker 网络内，Podman API 容器通过 host 网络和 `--add-host` 解析访问。

### 微信审核测试数据

线上最小审核数据使用 `site_id=1`，用于审核人员浏览首页、商品列表、商品详情并创建待支付订单。

```bash
cd server
python seed_admin.py
python seed_xijiao_demo_data.py
```

执行后会补齐商品、SKU、定价规则、未来库存、首页 Banner/公告和优惠规则。详情见 [docs/wechat_review_seed_data.md](docs/wechat_review_seed_data.md)。

### TKE / Kubernetes

仓库保留腾讯云 TKE 部署清单，适合后续迁移到云托管数据层与弹性扩容：

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-hpa.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/beat-deployment.yaml
kubectl apply -f k8s/admin-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

## 项目文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目总览 | [docs/project_overview.md](docs/project_overview.md) | 三端职责、代码入口、生产状态 |
| 技术架构 | [docs/architecture.md](docs/architecture.md) | 架构设计、数据模型、服务边界 |
| 生产运维 | [scripts/prod/README.md](scripts/prod/README.md) | Podman 蓝绿发布、健康检查、故障处理 |
| 测试报告 | [docs/test_report.md](docs/test_report.md) | 测试与合规总结 |
| 测试用例 | [docs/test_cases.md](docs/test_cases.md) | 端到端测试用例 |
| PRD 基线 | [prd/yyyl_prd.md](prd/yyyl_prd.md) | 产品需求基线 |
| PRD 增量 | [prd/yyyl_prd_v1.5_increment.md](prd/yyyl_prd_v1.5_increment.md) | 搭配售卖、秒杀、地图、内部管理等 |

## License

Private — All rights reserved.
