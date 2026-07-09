# 一月一露

> 多营地户外露营综合运营平台
> C 端小程序 + B 端管理后台 + FastAPI 后端 + Podman 蓝绿发布

一月一露（yyyl）服务于露营地的线上经营和现场运营，覆盖营位预订、装备租赁、活动报名、小商店、会员权益、微信支付、电子票核销、退款审批、财务结算、内容运营和多营地管理。

项目支持同一套代码运行多个营地：小程序按营地配置构建，后端通过 `X-Site-Id` 做全链路数据隔离。

## 当前状态

| 项目 | 状态 |
|------|------|
| 生产域名 | `https://www.yyylcamp.com` |
| 线上 API | Podman 蓝绿容器，Nginx 反向代理 |
| 当前基线 | v1.8 已完成生产发布；2026-07-09 下单、日期必选、出行人保存修复已上线，西郊小程序包已上传 |
| 多营地 | 西郊林场 `site_id=1`，大聋谷 `site_id=2` |
| 微信支付 | 真实 JSAPI 支付链路已接入；当前商户侧收款能力受限，真实支付可能返回 `NO_AUTH` |
| 图片资源 | 后端自动生成 `thumb` / `large` / `banner` 派生图，小程序和 Admin 按场景加载缩略图 |
| 小程序构建产物 | `uni-app/dist/build/mp-weixin-xijiao`、`uni-app/dist/build/mp-weixin-dalonggu` |

## 能力版图

| C 端小程序 | B 端管理后台 | 后端与运维 |
|------------|--------------|------------|
| 首页、分类、商品详情 | 商品、SKU、库存、价格日历 | FastAPI async API |
| 营位预订、活动报名 | 订单查询、退款审批、导出 | PostgreSQL 事务数据 |
| 购物车、订单确认、微信支付 | 会员、年卡、次数卡、积分 | Redis 缓存与队列 |
| 电子票、扫码核销、员工端 | 财务流水、结算、报表 | Celery 定时任务 |
| 智能客服、FAQ、内容页 | CMS 页面、素材库、Banner | Podman 蓝绿发布 |
| 多营地品牌配置 | 企业微信机器人配置 | Nginx 静态资源与反代 |

## 技术架构

```text
┌──────────────────────────────────────────────────────────────┐
│ C 端：uni-app 小程序 / H5                                      │
│ Vue3 + TypeScript + Pinia + SCSS                              │
│ VITE_SITE_CODE = xijiao / dalonggu                            │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS
                               │ X-Site-Id
┌──────────────────────────────▼───────────────────────────────┐
│ B 端：Vue3 管理后台                                             │
│ Vite + Element Plus + Pinia + ECharts                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
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
                                      │ 异步任务 / 定时 │
                                      └────────────────┘
```

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| 小程序 | uni-app、Vue3、TypeScript、Pinia、SCSS | 同代码库按营地构建 |
| 管理后台 | Vue3、Vite、Element Plus、Pinia、ECharts | 运营、财务、内容和系统管理 |
| 后端 API | FastAPI、SQLAlchemy 2.0 async、Pydantic v2 | REST API、权限、多营地隔离 |
| 数据层 | PostgreSQL、Redis | 订单、库存、支付、缓存和任务队列 |
| 异步任务 | Celery | 订单超时、统计、通知、结算等 |
| 部署 | Podman、Nginx、Fabric | 生产 API 蓝绿发布，静态资源独立发布 |

## 目录结构

```text
yyyl/
├── uni-app/                 # C 端小程序 / H5 / 员工端
│   ├── src/pages/           # 首页、分类、购物车、订单、支付、电子票等
│   ├── src/pages-sub/       # 分包页面：营地地图、互动功能等
│   ├── src/components/      # 业务组件与通用组件
│   ├── src/config/          # 多营地品牌配置
│   ├── src/store/           # Pinia 状态
│   └── src/utils/           # 请求、认证、图片、业务规则等工具
│
├── admin/                   # B 端管理后台
│   ├── src/api/             # Axios API 模块
│   ├── src/views/           # 商品、订单、会员、财务、CMS、系统设置等页面
│   ├── src/router/          # 路由与权限守卫
│   ├── src/stores/          # Pinia 状态
│   └── src/styles/          # SCSS 主题与 Element Plus 覆盖
│
├── server/                  # FastAPI 后端
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic 请求 / 响应模型
│   ├── routers/             # API 路由
│   ├── services/            # 业务服务层
│   ├── tasks/               # Celery 任务
│   ├── middleware/          # 认证、多营地隔离等中间件
│   ├── alembic/             # 数据库迁移
│   ├── images/              # 商品、Banner、CMS 图片
│   └── scripts/             # 后端维护脚本
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

## 快速启动

### 环境要求

| 工具 | 建议版本 | 用途 |
|------|----------|------|
| Node.js | 18+ | 小程序和管理后台构建 |
| npm | 9+ | Node 包管理 |
| Python | 3.11 | 后端运行时 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存、队列、会话 |
| 微信开发者工具 | 最新稳定版 | 小程序预览、上传和调试 |

后端开发默认使用本机 conda 环境：

```bash
conda activate yyyl
```

### 1. 启动基础服务

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

| 地址 | 说明 |
|------|------|
| `http://localhost:8000/health` | 健康检查 |
| `http://localhost:8000/docs` | Swagger API 文档 |
| `http://localhost:8000/redoc` | ReDoc API 文档 |

本地默认管理员为 `admin` / `admin123456`。生产环境必须更换默认账号、JWT 密钥、AES 密钥和所有第三方密钥。

### 3. 启动管理后台

```bash
cd admin
npm install
npm run dev
```

管理后台本地地址：`http://localhost:3000`。开发环境下 `/api` 默认代理到 `http://localhost:8000`。

### 4. 启动小程序

```bash
cd uni-app
npm install --force

# 西郊林场
npm run dev:wx:xijiao

# 大聋谷
npm run dev:wx:dalonggu

# H5 调试
npm run dev:h5:xijiao
```

生产构建：

```bash
cd uni-app
npm run build:wx:xijiao
npm run build:wx:dalonggu
```

构建后导入微信开发者工具：

| 营地 | 构建目录 |
|------|----------|
| 西郊林场 | `uni-app/dist/build/mp-weixin-xijiao` |
| 大聋谷 | `uni-app/dist/build/mp-weixin-dalonggu` |

## 常用命令

| 场景 | 命令 |
|------|------|
| 后端开发服务 | `cd server && uvicorn main:app --reload --port 8000` |
| 生成迁移 | `cd server && alembic revision --autogenerate -m "描述信息"` |
| 执行迁移 | `cd server && alembic upgrade head` |
| Celery Worker | `cd server && celery -A celery_app worker --loglevel=info` |
| Celery Beat | `cd server && celery -A celery_app beat --loglevel=info` |
| 管理后台开发 | `cd admin && npm run dev` |
| 管理后台构建 | `cd admin && npm run build` |
| 小程序类型检查 | `cd uni-app && npm run type-check` |
| 西郊小程序构建 | `cd uni-app && npm run build:wx:xijiao` |
| 大聋谷小程序构建 | `cd uni-app && npm run build:wx:dalonggu` |

## 多营地机制

| 营地 | site_id | 构建代号 | 说明 |
|------|---------|----------|------|
| 一月一露·西郊林场 | `1` | `xijiao` | 当前线上审核与测试主站点 |
| 一月一露·大聋谷 | `2` | `dalonggu` | 同代码库独立品牌配置 |

多营地规则：

- 小程序通过 `VITE_SITE_CODE` 在构建时选择营地品牌、主题、文案和接口配置。
- 后端从 `X-Site-Id` 请求头解析当前营地，核心业务查询必须按 `site_id` 过滤。
- 新增营地时，需要补充 `uni-app/src/config/sites.ts`、`.env.{site_code}`、构建脚本和后端站点白名单。

## 图片资源

项目静态图片由后端挂载到 `/images`，生产目录为 `/opt/yyyl/server/images`。为降低小程序首屏和列表加载压力，后端会为 JPG / PNG / WebP 自动生成派生图。

| 规格 | 路径 | 用途 |
|------|------|------|
| 原图 | `/images/...` | 上传源文件、详情兜底 |
| 缩略图 | `/images/thumb/...` | 商品卡片、素材库预览 |
| 大图 | `/images/large/...` | 商品详情轮播 |
| Banner | `/images/banner/...` | 首页和 CMS 横幅 |

旧图片补齐派生图：

```bash
ACTIVE_API=$(podman ps --format '{{.Names}}' | grep -E '^yyyl-api-(blue|green)$' | head -1)
podman exec "$ACTIVE_API" sh -lc 'cd /app && python scripts/generate_image_variants.py --images-root /app/images'
```

发布图片相关改动时，建议顺序为：

1. 发布后端 API，确认容器内 `/app/images` 可写。
2. 在活跃 API 容器内执行旧图补齐脚本。
3. 发布 Admin 静态资源。
4. 重新构建并上传小程序。

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
WECHAT_NOTIFY_URL=https://www.yyylcamp.com/api/v1/payments/wechat/notify
WECHAT_REFUND_NOTIFY_URL=https://www.yyylcamp.com/api/v1/payments/wechat/refund-notify

CAIYUN_API_TOKEN=your_caiyun_api_token
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

安全约定：

- 不提交真实密钥、证书、私钥、API Token 或带凭据的 DSN。
- 生产环境必须设置 `DEBUG=false`。
- 微信支付证书放在生产服务器安全目录中，由容器只读挂载。
- `.env`、证书文件、后台管理员密码不写入 README、PRD、CURRENT 或聊天记录。

## 业务模块

### 小程序端

| 模块 | 说明 |
|------|------|
| 首页 | Banner、天气、推荐商品、分类入口、CMS 配置内容 |
| 分类与商品 | 商品分类、搜索、筛选、SKU、价格、库存、图片变体 |
| 预订与购物车 | 营位日期选择、购物车报价、免责声明确认 |
| 订单与支付 | 订单确认、微信支付参数获取、支付结果处理 |
| 电子票与核销 | 电子票二维码、员工扫码核销、票券状态 |
| 会员权益 | 年卡、次数卡、积分、会员订单 |
| 智能客服 | FAQ、知识库问答、人工兜底和反馈 |

### 管理后台

| 模块 | 说明 |
|------|------|
| 工作台 | 销售、订单、会员、财务概览 |
| 商品与库存 | 商品、SKU、共享库存池、日期定价、上下架 |
| 订单与退款 | 订单查询、详情、导出、退款审批队列 |
| 会员与权益 | 用户、年卡、次数卡、积分 |
| 财务与报表 | 交易流水、结算、销售报表、导出 |
| 内容运营 | CMS 页面、素材库、Banner、公告、FAQ |
| 营地玩法 | 秒杀、搭配售卖、营地地图、活动配置 |
| 系统管理 | 员工、权限、高危操作确认、操作日志 |

### 后端 API

| 模块 | 前缀 |
|------|------|
| Auth | `/api/v1/auth` |
| Products | `/api/v1/products` |
| Orders | `/api/v1/orders` |
| Payments | `/api/v1/payments` |
| Cart | `/api/v1/cart` |
| Tickets | `/api/v1/tickets` |
| Members | `/api/v1/members` |
| Admin | `/api/v1/admin` |
| Reports | `/api/v1/admin/reports` |
| Content | `/api/v1/content` |
| Weather | `/api/v1/weather` |

## 设计系统

| 端 | 设计方向 |
|----|----------|
| 小程序 | “野奢 Organic Luxury Outdoor”：深苔绿、暖铜金、暖沙背景，强调自然材质、露营氛围和低摩擦下单链路 |
| 管理后台 | “深邃极光 Northern Lights Dashboard”：暗森林侧边栏、极光渐变、玻璃拟态卡片、工作台式信息密度 |

核心色彩：

| 用途 | 色值 |
|------|------|
| 深苔绿 | `#2d4a3e` |
| 暖铜金 | `#c8a872` |
| 暖沙背景 | `#faf6f0` |
| 后台森林绿 | `#3d8b5e` |
| 后台深色侧边栏 | `#141e1a` |

## 生产发布

生产 API 标准流程使用 Podman 蓝绿发布，不使用 conda 直接运行 FastAPI。

```bash
pip install -r scripts/ops/requirements.txt

fab info
fab preflight
fab build --tag=v0.1.0
fab deploy --tag=v0.1.0
fab health
fab rollback
```

如使用镜像仓库：

```bash
export YYYL_REGISTRY=ccr.ccs.tencentyun.com
export YYYL_NAMESPACE=your-namespace

fab registry-release-api --tag=v0.1.0
```

线上关键约定：

| 项目 | 说明 |
|------|------|
| Nginx 配置 | 必须包含 `upstream yyyl_api_backend`，发布脚本只替换 upstream 内端口 |
| API 容器 | `yyyl-api-blue` / `yyyl-api-green` |
| API 端口 | `8001` / `8002` |
| 静态图片 | Nginx 映射 `/images/` 到生产图片目录 |
| 微信支付证书 | 容器只读挂载，证书内容不得写入仓库 |
| 数据层过渡状态 | PostgreSQL / Redis 仍在 Docker 网络内，Podman API 可使用 host 网络和 `--add-host` 访问 |

当前生产快照以 `CURRENT.md` 为准。2026-07-06 后端/Admin 最新上线提交为 `715576f`，API 活跃容器为 `yyyl-api-green`，Nginx upstream 指向 `127.0.0.1:8002`，Admin 入口资源为 `/assets/index-wazgtEOT.js`。

详细运维手册见 [scripts/prod/README.md](scripts/prod/README.md)。

## 验证清单

文档或小改动至少运行：

```bash
git diff --check
```

图片优化相关回归：

```bash
PYTHONPATH=server python -m unittest server.tests.test_image_variants -v

cd uni-app
node --test tests/v18-product-flow.test.mjs
npm run type-check
```

上线前推荐完整检查：

```bash
cd server
conda run -n yyyl python -m unittest discover -s tests -p 'test_*.py' -v

cd ../admin
npm run build

cd ../uni-app
npm run type-check
npm run build:wx:xijiao
npm run build:wx:dalonggu
```

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目总览 | [docs/project_overview.md](docs/project_overview.md) | 三端职责、代码入口、生产状态 |
| 技术架构 | [docs/architecture.md](docs/architecture.md) | 架构设计、数据模型、服务边界 |
| 生产运维 | [scripts/prod/README.md](scripts/prod/README.md) | Podman 蓝绿发布、健康检查、故障处理 |
| 测试报告 | [docs/test_report.md](docs/test_report.md) | 测试与合规总结 |
| 测试用例 | [docs/test_cases.md](docs/test_cases.md) | 端到端测试用例 |
| 微信审核数据 | [docs/wechat_review_seed_data.md](docs/wechat_review_seed_data.md) | 审核演示数据准备 |
| PRD 基线 | [prd/yyyl_prd.md](prd/yyyl_prd.md) | 产品需求基线 |
| v1.8 上线审查 | [docs/v1.8_production_review.html](docs/v1.8_production_review.html) | 当前生产版本审查报告 |

## License

Private — All rights reserved.
