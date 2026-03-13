"""
某露营地 - FastAPI 应用入口
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import engine
from redis_client import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动 / 关闭时执行"""
    # ---- 启动 ----
    # 初始化 Redis
    await init_redis()
    print(f"[启动] Redis 连接已建立: {settings.REDIS_URL}")
    print(f"[启动] 数据库连接池已就绪: pool_size={settings.DATABASE_POOL_SIZE}")
    print(f"[启动] 应用环境: {settings.APP_ENV}")

    yield

    # ---- 关闭 ----
    await close_redis()
    await engine.dispose()
    print("[关闭] 所有连接已释放")


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.APP_NAME,
    description="某露营地微信小程序后端API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 健康检查 ----

@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---- 静态文件（商品图片等） ----
_images_dir = Path(__file__).resolve().parent / "images"
if _images_dir.is_dir():
    app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")

# ---- 路由注册 ----
from routers import (
    admin,
    auth,
    campsites,
    cart,
    content,
    finance,
    members,
    notifications,
    orders,
    products,
    reports,
    tickets,
    users,
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(cart.router)
app.include_router(members.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(finance.router)
app.include_router(admin.router)
app.include_router(campsites.router)
app.include_router(content.router)
app.include_router(notifications.router)
app.include_router(reports.router)
