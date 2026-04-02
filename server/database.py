"""
数据库连接管理
- 异步引擎 (create_async_engine)
- 异步会话工厂 (async_sessionmaker)
- FastAPI 依赖注入 get_db
- 同步引擎 + session（Celery 任务使用）
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from config import settings

# 异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # 连接健康检查
    pool_recycle=3600,  # 1小时回收连接
)

# 异步会话工厂
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：提供数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---- 同步引擎 + session（Celery 任务使用） ----

# 同步数据库 URL：将 asyncpg 驱动替换为 psycopg2
SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_size=5,
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(bind=sync_engine)


@contextmanager
def get_sync_session():
    """同步 session 上下文管理器，供 Celery worker 使用"""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
