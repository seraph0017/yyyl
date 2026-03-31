"""
某露营地 - FastAPI 应用入口
"""

from __future__ import annotations

import logging
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from database import engine
from redis_client import close_redis, init_redis

logger = logging.getLogger(__name__)


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


# ---- Request ID 中间件 ----

class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一 request_id，写入响应头和日志上下文"""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


# ---- 全局异常处理 ----

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数校验失败：返回结构化错误"""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        f"[请求校验失败] request_id={request_id} path={request.url.path} errors={exc.errors()}"
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": [
                {
                    "loc": list(err.get("loc", [])),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", ""),
                }
                for err in exc.errors()
            ],
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：记录完整堆栈，返回安全响应"""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        f"[未捕获异常] request_id={request_id} path={request.url.path}\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
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
    bundles,
    camp_maps,
    campsites,
    cart,
    content,
    expenses,
    finance,
    members,
    notifications,
    orders,
    performance,
    products,
    reports,
    seckill,
    tickets,
    users,
    weather,
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
app.include_router(bundles.router)
app.include_router(weather.router)
app.include_router(seckill.router)
app.include_router(camp_maps.router)
app.include_router(expenses.router)
app.include_router(performance.router)
