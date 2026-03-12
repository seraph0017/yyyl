"""
Celery 任务辅助工具

- 同步数据库会话（Celery Worker 是同步进程，不能用 asyncpg）
- 同步 Redis 客户端
- 任务监控装饰器
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Generator

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

logger = logging.getLogger("celery.tasks")

# ---- 同步数据库引擎（Celery Worker 用）----
# 将 asyncpg 驱动替换为 psycopg2（同步驱动）
_sync_db_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
).replace(
    "postgresql://", "postgresql+psycopg2://"
)

sync_engine = create_engine(
    _sync_db_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session)


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """获取同步数据库会话（上下文管理器）"""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---- 同步 Redis 客户端（Celery Worker 用）----
_sync_redis: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    """获取同步 Redis 客户端"""
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _sync_redis


# ---- 任务监控装饰器 ----
def task_monitor(task_func):
    """记录任务执行时间和结果"""
    @wraps(task_func)
    def wrapper(*args, **kwargs):
        task_name = task_func.__name__
        start = time.time()
        try:
            result = task_func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"[TASK_OK] {task_name} completed in {elapsed:.2f}s")
            if elapsed > 300:
                logger.warning(f"[TASK_SLOW] {task_name} took {elapsed:.2f}s (>5min)")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(
                f"[TASK_FAIL] {task_name} failed after {elapsed:.2f}s: {e}",
                exc_info=True,
            )
            raise
    return wrapper
