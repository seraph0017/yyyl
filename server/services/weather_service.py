"""
天气服务

- get_current_weather：获取当前天气（Redis 缓存）
- get_weather_forecast：获取未来天气预报（Redis 缓存）

使用 Redis 缓存策略：
- weather:current:{site_id} TTL=3600s (1h)
- weather:forecast:{site_id} TTL=3600s (1h)
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from redis_client import get_redis

logger = logging.getLogger(__name__)

# Redis 缓存 TTL（秒）
WEATHER_CURRENT_TTL = 3600  # 1小时
WEATHER_FORECAST_TTL = 3600  # 1小时

# 缓存 key 模板
CURRENT_KEY = "weather:current:{site_id}"
FORECAST_KEY = "weather:forecast:{site_id}"


async def get_current_weather(site_id: int = 1) -> Dict[str, Any]:
    """获取当前天气

    先查 Redis 缓存，未命中则调用第三方天气 API，结果写入缓存。

    Args:
        site_id: 营地ID

    Returns:
        当前天气数据
    """
    redis = get_redis()
    cache_key = CURRENT_KEY.format(site_id=site_id)

    # 查缓存
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"[天气] 缓存命中: key={cache_key}")
        return json.loads(cached)

    # 未命中，调用第三方 API
    weather_data = await _fetch_current_weather(site_id)

    # 写入缓存
    await redis.set(cache_key, json.dumps(weather_data, ensure_ascii=False), ex=WEATHER_CURRENT_TTL)
    logger.info(f"[天气] 获取当前天气: site_id={site_id}")

    return weather_data


async def get_weather_forecast(site_id: int = 1, days: int = 7) -> Dict[str, Any]:
    """获取未来天气预报

    先查 Redis 缓存，未命中则调用第三方天气 API，结果写入缓存。

    Args:
        site_id: 营地ID
        days: 预报天数（默认7天）

    Returns:
        天气预报数据
    """
    redis = get_redis()
    cache_key = FORECAST_KEY.format(site_id=site_id)

    # 查缓存
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"[天气] 预报缓存命中: key={cache_key}")
        data = json.loads(cached)
        # 按请求天数截取
        data["forecasts"] = data.get("forecasts", [])[:days]
        return data

    # 未命中，调用第三方 API
    forecast_data = await _fetch_weather_forecast(site_id, days)

    # 写入缓存
    await redis.set(
        cache_key,
        json.dumps(forecast_data, ensure_ascii=False, default=str),
        ex=WEATHER_FORECAST_TTL,
    )
    logger.info(f"[天气] 获取天气预报: site_id={site_id}, days={days}")

    return forecast_data


# ---- 内部方法：第三方 API 对接 ----

async def _fetch_current_weather(site_id: int) -> Dict[str, Any]:
    """调用第三方天气 API 获取当前天气

    TODO: 接入真实天气 API（和风天气、高德天气等）
    目前返回模拟数据

    Args:
        site_id: 营地ID

    Returns:
        当前天气数据
    """
    # TODO: 根据 site_id 查询营地经纬度，调用天气 API
    logger.warning(f"[天气] 使用模拟数据: site_id={site_id}")

    return {
        "temperature": 22.5,
        "weather": "多云",
        "wind": "东南风2级",
        "humidity": 65,
        "sunrise": "06:15",
        "sunset": "18:32",
        "icon": "cloudy",
        "description": "多云转晴，适宜户外露营活动",
    }


async def _fetch_weather_forecast(site_id: int, days: int) -> Dict[str, Any]:
    """调用第三方天气 API 获取未来天气预报

    TODO: 接入真实天气 API
    目前返回模拟数据

    Args:
        site_id: 营地ID
        days: 预报天数

    Returns:
        天气预报数据
    """
    logger.warning(f"[天气] 预报使用模拟数据: site_id={site_id}, days={days}")

    today = date.today()
    forecasts = []

    # 模拟数据
    weather_types = [
        ("晴", "sunny", 15, 26),
        ("多云", "cloudy", 16, 25),
        ("小雨", "rainy", 14, 22),
        ("晴", "sunny", 17, 28),
        ("阴", "overcast", 15, 23),
        ("多云", "cloudy", 16, 24),
        ("晴", "sunny", 18, 29),
    ]

    for i in range(min(days, 7)):
        w = weather_types[i % len(weather_types)]
        forecasts.append({
            "date": str(today + timedelta(days=i)),
            "temperature_min": w[2],
            "temperature_max": w[3],
            "weather": w[0],
            "icon": w[1],
        })

    return {"forecasts": forecasts}
