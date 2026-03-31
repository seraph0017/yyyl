# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

一月一露 (yyyl) — A multi-campsite outdoor camping operations platform. Full-stack: uni-app mini-program (C-end) + Vue3 admin dashboard (B-end) + FastAPI backend. Supports multiple campsites (西郊林场 site_id=1, 大聋谷 site_id=2) with data isolation via `X-Site-Id` header.

## Development Commands

### Backend (server/)
```bash
cd server && conda activate yyyl

# Dev server (hot reload)
uvicorn main:app --reload --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Seed data (first time only)
python seed_admin.py        # default: admin / admin123456
python seed_products.py     # sample products with SKUs

# Celery worker + beat (separate terminals)
celery -A celery_app worker --loglevel=info
celery -A celery_app beat --loglevel=info
```

### Admin Dashboard (admin/)
```bash
cd admin
npm install
npm run dev       # http://localhost:3000, proxies /api → localhost:8000
npm run build     # vue-tsc + vite build
```

### uni-app Mini Program (uni-app/)
```bash
cd uni-app
npm install --force   # --force required for @dcloudio dependency tree

# Dev (WeChat mini-program)
npm run dev:wx:xijiao
npm run dev:wx:dalonggu

# Dev (H5)
npm run dev:h5:xijiao

# Production build
npm run build:wx:xijiao
npm run build:wx:dalonggu

# Type check
npm run type-check
```

Build output: `dist/build/mp-weixin/` → import into WeChat DevTools.

### Infrastructure
```bash
# PostgreSQL + Redis via Docker
docker run -d --name yyyl-postgres -e POSTGRES_DB=yyyl -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15
docker run -d --name yyyl-redis -p 6379:6379 redis:7-alpine

# Full stack via Docker Compose
docker-compose up -d --build
```

## Architecture

### Three-Tier Structure
- **uni-app/** — C-end cross-platform mini-program (Vue3 + TS + Pinia + SCSS). Same codebase, different campsites via `VITE_SITE_CODE` env var at build time.
- **admin/** — B-end management dashboard (Vue3 + TS + Element Plus + Pinia + ECharts). Path alias `@` → `src/`.
- **server/** — FastAPI backend (Python 3.11 + SQLAlchemy 2.0 async + PostgreSQL + Redis + Celery).

### Multi-Campsite Isolation
- Frontend: `VITE_SITE_CODE` selects campsite brand/theme at build time. Config in `uni-app/src/config/sites.ts`.
- Backend: Every API filters by `site_id` extracted from `X-Site-Id` request header (`middleware/site.py`). Default is 1 (西郊林场).
- Adding a new campsite: add to `sites.ts`, create `.env.{code}`, add build scripts to `package.json`, allow new site_id in `middleware/site.py`.

### Backend Layers (server/)
- **models/** — SQLAlchemy models (56+ tables). All inherit from `models/base.py` which provides `id`, `created_at`, `updated_at`, `is_deleted` (soft delete).
- **schemas/** — Pydantic v2 request/response models.
- **routers/** — 19 API route modules, all prefixed `/api/v1/`. Registered in `main.py`.
- **services/** — Business logic layer (14 services).
- **tasks/** — Celery async tasks (25 scheduled tasks). Config in `celery_config.py`, app instance in `celery_app.py`.
- **middleware/** — `auth.py` (JWT auth), `site.py` (campsite isolation).
- **config.py** — pydantic-settings singleton loading from `.env`.
- **database.py** — Async SQLAlchemy engine + session factory + `get_db()` dependency.

### Admin Dashboard Layers (admin/src/)
- **api/** — 15 API modules (axios-based).
- **views/** — 24 page views.
- **router/** — Vue Router config with permission guards.
- **stores/** — Pinia state management.
- **styles/** — SCSS theme system with CSS variables (`--color-primary`, `--color-accent`, etc.). Element Plus theme override via `styles/element.scss`.
- Auto-import configured: Vue/VueRouter/Pinia APIs and Element Plus components are auto-imported (unplugin).

### uni-app Layers (uni-app/src/)
- **pages/** — 17 main pages (Vue3 SFC).
- **pages-sub/** — Subpackage pages (campsite map, games).
- **components/** — Shared components.
- **config/** — Campsite brand config (`sites.ts`).
- **store/** — Pinia stores.
- **utils/request.ts** — HTTP client, reads `VITE_API_BASE_URL`.

## Key Conventions

- **Language**: All code comments, commit messages, PRD, and docs are in Chinese.
- **Soft delete**: All models use `is_deleted` flag, never hard delete.
- **Async everywhere**: Backend uses async SQLAlchemy (`asyncpg`), async Redis. DB session via `get_db()` FastAPI dependency with auto commit/rollback.
- **API docs**: Available at `/docs` (Swagger) and `/redoc` in development mode only (disabled when `DEBUG=false`).
- **Environment config**: Backend reads from `server/.env` via pydantic-settings. Template at `server/.env.example`.
- **Static files**: Product images served from `server/images/` mounted at `/images`.

## Design Systems

- **Mini-program**: "野奢" (Organic Luxury Outdoor) — wabi-sabi aesthetics. Colors: deep moss green `#2d4a3e` + warm copper gold `#c8a872` + warm sand `#faf6f0`.
- **Admin dashboard**: "深邃极光" (Northern Lights Dashboard) — dark forest sidebar + aurora gradients + glassmorphism cards. Action buttons: 32px circular icon buttons with 11 color variants and hover glow effects (`action-btn--edit`, `action-btn--delete`, etc.).

## 需求→PRD→开发工作流

所有新功能开发遵循以下标准流程：

### 1. 需求提交
- 用户将新需求文档放入 `needs/{日期}/` 目录（如 `needs/0331/new-need.md`）
- 需求文档为自然语言描述，无格式要求

### 2. PRD 撰写（产品 Agent）
- **产品 Agent** 基于 `needs/` 中的新需求，结合现有 PRD 基线，撰写增量 PRD 文档
- PRD 输出到 `prd/` 目录，命名格式：`yyyl_prd_v{版本号}_increment.md`
- PRD 包含：变更总览、功能描述、用户故事、业务规则、数据模型变更、API 变更、前端变更、异常处理、验收标准、数据库索引设计、兼容性分析

### 3. 架构师评审（架构师 Agent）
- **架构师 Agent** 对 PRD 进行严格评审，维度包括：数据模型完备性、API 设计合理性、前端架构可行性、安全性、业务规则严密性、系统兼容性
- 评审输出：逐维度评分（1-10）+ 加权总分 + 必须修补的问题（CRITICAL/HIGH）+ 改进建议（MEDIUM）

### 4. 迭代修订
- 产品 Agent 根据架构师反馈修订 PRD
- 架构师 Agent 进行复审确认
- **反复迭代直到架构师评审评分 ≥ 8.5 且结论为 APPROVED**

### 5. 进入开发
- PRD 达到 APPROVED 状态后，方可进入开发阶段
- 开发遵循现有的 TDD + Code Review 工作流

### PRD 版本历史
| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| v1.4 | 2026-03-11 | ✅ 正式基线 | 初始 PRD，全功能定义 |
| v1.5 | 2026-03-15 | ✅ 架构师 APPROVED (9.0+) | 增量：搭配售卖、秒杀完善、前端增强、退款增强、工作系统 |
| v1.6 | 2026-03-31 | ✅ 架构师 APPROVED (8.8) | 增量：小程序可视化装修系统、企业宣传首页 |
