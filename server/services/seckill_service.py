"""
秒杀增强服务

- save_seckill_prefill：保存秒杀预填数据到 Redis
- get_seckill_prefill：获取预填数据
- get_seckill_status：获取秒杀实时状态（C端）
- get_seckill_monitor：获取秒杀监控数据（B端）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Redis key 模板
PREFILL_KEY = "seckill:prefill:{product_id}:{user_id}"
STOCK_KEY = "seckill_stock:{product_id}:{date}"
ONLINE_KEY = "seckill:online:{product_id}"
MONITOR_KEY = "seckill:monitor:{product_id}"

# TTL
PREFILL_TTL = 86400  # 预填数据保留24小时
ONLINE_MEMBER_TTL = 60  # 在线用户心跳60秒过期


async def save_seckill_prefill(
    redis: aioredis.Redis,
    product_id: int,
    user_id: int,
    data: Dict[str, Any],
) -> bool:
    """保存秒杀预填数据到 Redis

    在秒杀开始前，用户可以预先填写出行人、联系方式等信息，
    秒杀开始时直接提交，减少操作时间。

    Args:
        redis: Redis 客户端
        product_id: 秒杀商品ID
        user_id: 用户ID
        data: 预填数据

    Returns:
        是否保存成功
    """
    key = PREFILL_KEY.format(product_id=product_id, user_id=user_id)

    prefill_data = {
        "product_id": product_id,
        "identity_ids": data.get("identity_ids", []),
        "phone": data.get("phone"),
        "disclaimer_signed": data.get("disclaimer_signed", False),
        "bundle_items": data.get("bundle_items"),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    await redis.set(
        key,
        json.dumps(prefill_data, ensure_ascii=False),
        ex=PREFILL_TTL,
    )

    logger.info(
        f"[秒杀] 保存预填: product_id={product_id}, user_id={user_id}"
    )
    return True


async def get_seckill_prefill(
    redis: aioredis.Redis,
    product_id: int,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """获取秒杀预填数据

    Args:
        redis: Redis 客户端
        product_id: 秒杀商品ID
        user_id: 用户ID

    Returns:
        预填数据或 None
    """
    key = PREFILL_KEY.format(product_id=product_id, user_id=user_id)

    cached = await redis.get(key)
    if cached is None:
        return None

    return json.loads(cached)


async def get_seckill_status(
    redis: aioredis.Redis,
    product_id: int,
    booking_date: Optional[str] = None,
) -> Dict[str, Any]:
    """获取秒杀实时状态（C端）

    Args:
        redis: Redis 客户端
        product_id: 秒杀商品ID
        booking_date: 预约日期（YYYY-MM-DD）

    Returns:
        秒杀实时状态
    """
    # 剩余库存
    remaining_stock = 0
    if booking_date:
        stock_key = STOCK_KEY.format(product_id=product_id, date=booking_date)
        stock_val = await redis.get(stock_key)
        remaining_stock = int(stock_val) if stock_val else 0

    # 在线人数（通过 Sorted Set 的近期心跳数计算）
    online_key = ONLINE_KEY.format(product_id=product_id)
    now = datetime.now(timezone.utc).timestamp()
    # 清除过期的在线用户（超过60秒未心跳）
    await redis.zremrangebyscore(online_key, "-inf", now - ONLINE_MEMBER_TTL)
    online_count = await redis.zcard(online_key)

    # 确定状态
    if remaining_stock <= 0:
        seckill_status = "sold_out"
    else:
        seckill_status = "active"

    return {
        "product_id": product_id,
        "remaining_stock": max(remaining_stock, 0),
        "online_count": online_count or 0,
        "status": seckill_status,
    }


async def get_seckill_monitor(
    redis: aioredis.Redis,
    product_id: int,
    booking_date: Optional[str] = None,
) -> Dict[str, Any]:
    """获取秒杀监控数据（B端）

    Args:
        redis: Redis 客户端
        product_id: 秒杀商品ID
        booking_date: 预约日期

    Returns:
        秒杀监控数据
    """
    monitor_key = MONITOR_KEY.format(product_id=product_id)

    # 基础数据
    remaining_stock = 0
    if booking_date:
        stock_key = STOCK_KEY.format(product_id=product_id, date=booking_date)
        stock_val = await redis.get(stock_key)
        remaining_stock = int(stock_val) if stock_val else 0

    # 在线人数
    online_key = ONLINE_KEY.format(product_id=product_id)
    now = datetime.now(timezone.utc).timestamp()
    await redis.zremrangebyscore(online_key, "-inf", now - ONLINE_MEMBER_TTL)
    online_count = await redis.zcard(online_key)

    # 订单统计（从 Redis 计数器读取）
    orders_created = int(await redis.hget(monitor_key, "orders_created") or 0)
    orders_paid = int(await redis.hget(monitor_key, "orders_paid") or 0)
    peak_qps = int(await redis.hget(monitor_key, "peak_qps") or 0)

    return {
        "product_id": product_id,
        "online_count": online_count or 0,
        "remaining_stock": max(remaining_stock, 0),
        "orders_created": orders_created,
        "orders_paid": orders_paid,
        "peak_qps": peak_qps,
    }
