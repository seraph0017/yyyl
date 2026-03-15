"""
天气相关 Schemas

- WeatherCurrent：当前天气
- WeatherForecast：天气预报
- WeatherForecastResponse：预报响应
"""

import datetime as _dt
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

DateType = _dt.date


class WeatherCurrent(BaseModel):
    """当前天气"""

    model_config = ConfigDict(populate_by_name=True)

    temperature: float = Field(description="当前温度（℃）")
    weather: str = Field(description="天气状况（如：晴、多云）")
    wind: str = Field(description="风向风力（如：东风3级）")
    humidity: int = Field(description="相对湿度（%）")
    sunrise: str = Field(description="日出时间（HH:MM）")
    sunset: str = Field(description="日落时间（HH:MM）")
    icon: str = Field(description="天气图标编码")
    description: str = Field(description="天气描述文案")


class WeatherForecast(BaseModel):
    """单日天气预报"""

    model_config = ConfigDict(populate_by_name=True)

    date: DateType = Field(description="日期")
    temperature_min: float = Field(description="最低温度（℃）")
    temperature_max: float = Field(description="最高温度（℃）")
    weather: str = Field(description="天气状况")
    icon: str = Field(description="天气图标编码")


class WeatherForecastResponse(BaseModel):
    """天气预报响应"""

    model_config = ConfigDict(populate_by_name=True)

    forecasts: List[WeatherForecast] = Field(
        default_factory=list, description="天气预报列表",
    )
