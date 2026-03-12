"""
Redis 连接管理
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from config import settings

# 全局 Redis 客户端实例
redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """初始化 Redis 连接"""
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    # 验证连接
    await redis_client.ping()
    return redis_client


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端（FastAPI 依赖注入或直接调用）"""
    if redis_client is None:
        raise RuntimeError("Redis 客户端未初始化，请先调用 init_redis()")
    return redis_client
