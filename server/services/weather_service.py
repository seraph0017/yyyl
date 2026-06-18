"""
天气服务

数据源优先使用彩云天气 API。为了避免小程序每次打开页面都打到第三方接口，
服务进程内按站点和数据类型缓存 30 分钟；未配置 token 或接口异常时返回兜底数据。
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from config import settings

logger = logging.getLogger(__name__)

WEATHER_CACHE_TTL_SECONDS = 1800
CURRENT_KEY = "current:{site_id}"
FORECAST_KEY = "forecast:{site_id}"

SITE_LOCATIONS: dict[int, dict[str, float | str]] = {
    1: {"name": "一月一露·西郊林场", "longitude": 121.120115, "latitude": 30.955131},
    2: {"name": "一月一露·大聋谷", "longitude": 120.1, "latitude": 30.2},
}

_memory_cache: dict[str, tuple[float, Dict[str, Any]]] = {}

SKYCON_MAP: dict[str, tuple[str, str]] = {
    "CLEAR_DAY": ("晴", "☀️"),
    "CLEAR_NIGHT": ("晴", "🌙"),
    "PARTLY_CLOUDY_DAY": ("多云", "⛅"),
    "PARTLY_CLOUDY_NIGHT": ("多云", "☁️"),
    "CLOUDY": ("阴", "☁️"),
    "LIGHT_HAZE": ("轻度雾霾", "🌫️"),
    "MODERATE_HAZE": ("中度雾霾", "🌫️"),
    "HEAVY_HAZE": ("重度雾霾", "🌫️"),
    "LIGHT_RAIN": ("小雨", "🌦️"),
    "MODERATE_RAIN": ("中雨", "🌧️"),
    "HEAVY_RAIN": ("大雨", "🌧️"),
    "STORM_RAIN": ("暴雨", "⛈️"),
    "FOG": ("雾", "🌫️"),
    "LIGHT_SNOW": ("小雪", "🌨️"),
    "MODERATE_SNOW": ("中雪", "🌨️"),
    "HEAVY_SNOW": ("大雪", "🌨️"),
    "STORM_SNOW": ("暴雪", "❄️"),
    "DUST": ("浮尘", "🌫️"),
    "SAND": ("沙尘", "🌫️"),
    "WIND": ("大风", "💨"),
}


def clear_weather_memory_cache() -> None:
    """清空进程内天气缓存，供测试和必要的运维调试使用。"""
    _memory_cache.clear()


async def get_current_weather(site_id: int = 1) -> Dict[str, Any]:
    """获取当前天气和未来小时级预报。"""
    cache_key = CURRENT_KEY.format(site_id=site_id)
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        weather_data = await _fetch_current_weather(site_id)
    except Exception as exc:
        logger.warning("[天气] 当前天气获取失败，使用兜底数据: site_id=%s, error=%s", site_id, exc)
        weather_data = _fallback_current_weather(site_id)

    _set_cached(cache_key, weather_data)
    return weather_data


async def get_weather_forecast(site_id: int = 1, days: int = 7) -> Dict[str, Any]:
    """获取未来每日天气预报。"""
    cache_key = FORECAST_KEY.format(site_id=site_id)
    cached = _get_cached(cache_key)
    if cached:
        data = {"forecasts": cached.get("forecasts", [])[:days]}
        return data

    try:
        forecast_data = await _fetch_weather_forecast(site_id, days)
    except Exception as exc:
        logger.warning("[天气] 天气预报获取失败，使用兜底数据: site_id=%s, error=%s", site_id, exc)
        forecast_data = _fallback_weather_forecast(site_id, days)

    _set_cached(cache_key, forecast_data)
    forecast_data["forecasts"] = forecast_data.get("forecasts", [])[:days]
    return forecast_data


def _get_cached(cache_key: str) -> Optional[Dict[str, Any]]:
    cached = _memory_cache.get(cache_key)
    if not cached:
        return None
    expires_at, data = cached
    if expires_at <= time.time():
        _memory_cache.pop(cache_key, None)
        return None
    return data.copy()


def _set_cached(cache_key: str, data: Dict[str, Any]) -> None:
    _memory_cache[cache_key] = (time.time() + WEATHER_CACHE_TTL_SECONDS, data.copy())


async def _fetch_current_weather(site_id: int) -> Dict[str, Any]:
    payload = await _request_caiyun_weather(site_id, mode="current", steps=12)
    data = _parse_caiyun_current(payload)
    data["location_name"] = str(_get_site_location(site_id)["name"])
    return data


async def _fetch_weather_forecast(site_id: int, days: int) -> Dict[str, Any]:
    payload = await _request_caiyun_weather(site_id, mode="daily", steps=max(days, 7))
    data = _parse_caiyun_daily(payload, days)
    data["location_name"] = str(_get_site_location(site_id)["name"])
    return data


async def _request_caiyun_weather(site_id: int, mode: str, steps: int) -> Dict[str, Any]:
    if not settings.CAIYUN_API_TOKEN:
        raise RuntimeError("CAIYUN_API_TOKEN 未配置")

    location = _get_site_location(site_id)
    longitude = location["longitude"]
    latitude = location["latitude"]
    url = (
        f"{settings.CAIYUN_BASE_URL.rstrip('/')}/v2.7/"
        f"{settings.CAIYUN_API_TOKEN}/{longitude},{latitude}/weather"
    )

    if mode == "daily":
        params = {
            "dailysteps": steps,
            "granu": "daily,hourly",
            "begin": int(time.time()),
            "fields": "skycon,tmp,prc,wnd",
            "lang": "zh_CN",
            "unit": "metric:v2",
            "cncast": "true",
        }
    else:
        params = {
            "granu": "minutely,hourly",
            "alert": "true",
            "fields": "skycon,precipitation,alert,wind,tmp",
            "unit": "metric:v2",
            "hourlysteps": steps,
            "lang": "zh_CN",
            "span": 16,
            "cncast": "true",
        }

    async with httpx.AsyncClient(timeout=settings.CAIYUN_TIMEOUT_SECONDS) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, dict) or data.get("status") not in (None, "ok"):
        raise RuntimeError(f"彩云天气响应异常: {str(data)[:300]}")
    return data


def _parse_caiyun_current(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = _dict(payload.get("result"))
    realtime = _dict(result.get("realtime"))
    hourly = _dict(result.get("hourly"))
    minutely = _dict(result.get("minutely"))

    weather, icon = _skycon_to_weather(str(realtime.get("skycon") or "PARTLY_CLOUDY_DAY"))
    temperature = _round_float(realtime.get("temperature"), 1, 0)
    humidity = _normalize_humidity(realtime.get("humidity"))
    wind = _format_wind(_dict(realtime.get("wind")))

    return {
        "temperature": temperature,
        "weather": weather,
        "wind": wind,
        "humidity": humidity,
        "sunrise": "06:00",
        "sunset": "18:30",
        "icon": icon,
        "description": _weather_description(weather, minutely.get("description"), realtime),
        "hourly_forecasts": _parse_caiyun_hourly(hourly),
        "updated_at": int(payload.get("server_time") or time.time()),
    }


def _parse_caiyun_hourly(hourly: Dict[str, Any]) -> List[Dict[str, Any]]:
    skycon_items = _index_items(hourly.get("skycon"))
    temperature_items = _index_items(hourly.get("temperature"))
    precipitation_items = _index_items(hourly.get("precipitation"))
    datetimes = _ordered_datetimes(skycon_items, temperature_items, precipitation_items)
    forecasts: list[dict[str, Any]] = []

    for dt in datetimes[:12]:
        skycon = skycon_items.get(dt, {}).get("value") or "PARTLY_CLOUDY_DAY"
        weather, icon = _skycon_to_weather(str(skycon))
        precipitation = precipitation_items.get(dt, {})
        forecasts.append({
            "datetime": dt,
            "time": _format_hour(dt),
            "temperature": _round_float(temperature_items.get(dt, {}).get("value"), 1, 0),
            "weather": weather,
            "icon": icon,
            "precipitation": _round_float(precipitation.get("value"), 2, 0),
            "precipitation_probability": _normalize_probability(precipitation.get("probability")),
        })
    return forecasts


def _parse_caiyun_daily(payload: Dict[str, Any], days: int) -> Dict[str, Any]:
    daily = _dict(_dict(payload.get("result")).get("daily"))
    skycon_items = _index_items(daily.get("skycon"), key_name="date")
    temperature_items = _index_items(daily.get("temperature"), key_name="date")
    precipitation_items = _index_items(daily.get("precipitation"), key_name="date")
    dates = _ordered_datetimes(skycon_items, temperature_items, precipitation_items)

    forecasts: list[dict[str, Any]] = []
    for dt in dates[:days]:
        skycon = skycon_items.get(dt, {}).get("value") or "PARTLY_CLOUDY_DAY"
        weather, icon = _skycon_to_weather(str(skycon))
        temperature = temperature_items.get(dt, {})
        precipitation = precipitation_items.get(dt, {})
        forecasts.append({
            "date": dt[:10],
            "temperature_min": _round_float(temperature.get("min"), 1, 0),
            "temperature_max": _round_float(temperature.get("max"), 1, 0),
            "weather": weather,
            "icon": icon,
            "precipitation_probability": _normalize_probability(precipitation.get("probability")),
        })
    return {"forecasts": forecasts}


def _fallback_current_weather(site_id: int) -> Dict[str, Any]:
    return {
        "location_name": str(_get_site_location(site_id)["name"]),
        "temperature": 22.5,
        "weather": "多云",
        "wind": "东南风2级",
        "humidity": 65,
        "sunrise": "06:15",
        "sunset": "18:32",
        "icon": "⛅",
        "description": "多云转晴，适宜户外露营活动",
        "hourly_forecasts": _fallback_hourly_forecasts(),
        "updated_at": int(time.time()),
    }


def _fallback_weather_forecast(site_id: int, days: int) -> Dict[str, Any]:
    today = date.today()
    weather_types = [
        ("晴", "☀️", 15, 26, 10),
        ("多云", "⛅", 16, 25, 20),
        ("小雨", "🌦️", 14, 22, 65),
        ("晴", "☀️", 17, 28, 10),
        ("阴", "☁️", 15, 23, 30),
        ("多云", "⛅", 16, 24, 20),
        ("晴", "☀️", 18, 29, 5),
    ]
    forecasts = []
    for i in range(min(days, 7)):
        weather, icon, temp_min, temp_max, probability = weather_types[i % len(weather_types)]
        forecasts.append({
            "date": str(today + timedelta(days=i)),
            "temperature_min": temp_min,
            "temperature_max": temp_max,
            "weather": weather,
            "icon": icon,
            "precipitation_probability": probability,
        })
    return {"location_name": str(_get_site_location(site_id)["name"]), "forecasts": forecasts}


def _fallback_hourly_forecasts() -> list[dict[str, Any]]:
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    forecasts = []
    for i in range(6):
        dt = now + timedelta(hours=i)
        forecasts.append({
            "datetime": dt.isoformat(),
            "time": f"{dt.hour:02d}:00",
            "temperature": 22 + i % 3,
            "weather": "多云",
            "icon": "⛅",
            "precipitation": 0,
            "precipitation_probability": 20,
        })
    return forecasts


def _get_site_location(site_id: int) -> dict[str, float | str]:
    return SITE_LOCATIONS.get(site_id) or SITE_LOCATIONS[1]


def _skycon_to_weather(skycon: str) -> Tuple[str, str]:
    return SKYCON_MAP.get(skycon, ("多云", "⛅"))


def _weather_description(weather: str, minutely_description: Any, realtime: Dict[str, Any]) -> str:
    if isinstance(minutely_description, str) and minutely_description:
        return minutely_description
    precipitation = _dict(_dict(realtime.get("precipitation")).get("local"))
    intensity = _round_float(precipitation.get("intensity"), 2, 0)
    if intensity > 0:
        return f"当前有降水，强度 {intensity} mm/h"
    return f"当前{weather}，适合关注营地出行安排"


def _index_items(value: Any, key_name: str = "datetime") -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        key = item.get(key_name) or item.get("date") or item.get("datetime")
        if isinstance(key, str):
            indexed[key] = item
    return indexed


def _ordered_datetimes(*sources: dict[str, dict[str, Any]]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for source in sources:
        for key in source.keys():
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    return sorted(ordered)


def _format_hour(datetime_str: str) -> str:
    try:
        return datetime.fromisoformat(datetime_str.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return datetime_str[11:16] if len(datetime_str) >= 16 else datetime_str


def _format_wind(wind: Dict[str, Any]) -> str:
    direction = _wind_direction(wind.get("direction"))
    level = _wind_level(wind.get("speed"))
    return f"{direction}{level}级"


def _wind_direction(value: Any) -> str:
    try:
        degree = float(value) % 360
    except (TypeError, ValueError):
        return "微风"
    directions = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    index = int((degree + 22.5) // 45) % 8
    return directions[index]


def _wind_level(value: Any) -> int:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return 1
    if speed < 1:
        return 0
    if speed < 6:
        return 1
    if speed < 12:
        return 2
    if speed < 20:
        return 3
    if speed < 29:
        return 4
    return 5


def _normalize_humidity(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 <= number <= 1:
        number *= 100
    return max(0, min(100, int(round(number))))


def _normalize_probability(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 <= number <= 1:
        number *= 100
    return max(0, min(100, int(round(number))))


def _round_float(value: Any, digits: int, default: float) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return default


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}
