"""
天气路由

- GET /api/v1/weather/current   — 当前天气（🌐 游客可访问）
- GET /api/v1/weather/forecast  — 未来7天预报（🌐 游客可访问）

通过请求头 X-Site-Id 确定营地位置。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from middleware.auth import get_optional_user
from middleware.site import get_site_id
from models.user import User
from schemas.common import ResponseModel
from schemas.weather import WeatherCurrent, WeatherForecastResponse
from services import weather_service

router = APIRouter(tags=["天气"])


@router.get("/api/v1/weather/current", summary="当前天气")
async def get_current_weather(
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
):
    """获取营地当前天气（游客可访问）

    通过 X-Site-Id header 确定营地。
    数据缓存在 Redis，TTL=1小时。
    """
    site_id = get_site_id(request)
    weather_data = await weather_service.get_current_weather(site_id=site_id)
    result = WeatherCurrent.model_validate(weather_data)
    return ResponseModel.success(data=result)


@router.get("/api/v1/weather/forecast", summary="天气预报")
async def get_weather_forecast(
    request: Request,
    days: int = Query(default=7, ge=1, le=7, description="预报天数（1-7）"),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取营地未来天气预报（游客可访问）

    通过 X-Site-Id header 确定营地。
    数据缓存在 Redis，TTL=1小时。
    """
    site_id = get_site_id(request)
    forecast_data = await weather_service.get_weather_forecast(
        site_id=site_id, days=days,
    )
    result = WeatherForecastResponse.model_validate(forecast_data)
    return ResponseModel.success(data=result)
