"""
应用配置管理
使用 pydantic-settings 从环境变量 / .env 文件加载配置
"""

from __future__ import annotations

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，所有敏感信息从环境变量读取"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ---- 应用配置 ----
    APP_NAME: str = "一月一露"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # ---- 数据库配置 ----
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/yyyl"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # ---- Redis配置 ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- JWT配置 ----
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2小时
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7天

    # ---- 微信小程序配置（默认/西郊林场） ----
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # ---- 多营地微信 appid 映射 ----
    # JSON格式: {"1": {"app_id": "wxXXX", "app_secret": "xxx"}, "2": {...}}
    WECHAT_APPS: str = '{}'

    # ---- 微信支付配置 ----
    WECHAT_MCH_ID: str = ""
    WECHAT_API_KEY: str = ""
    WECHAT_CERT_PATH: str = ""
    WECHAT_KEY_PATH: str = ""
    WECHAT_NOTIFY_URL: str = ""

    # ---- 抖音小程序配置（预留） ----
    DOUYIN_APPS: str = '{}'

    # ---- 小红书小程序配置（预留） ----
    XHS_APPS: str = '{}'

    # ---- AES加密配置 ----
    AES_ENCRYPTION_KEY: str = "change-me-32-byte-key-in-prod!!"

    # ---- CORS配置 ----
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8080"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """解析CORS来源列表"""
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    # ---- 日志配置 ----
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


# 全局单例
settings = Settings()
