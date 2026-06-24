"""
v1.7 小程序码 Schema
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


QRCODE_TARGET_TYPES = {
    "category",
    "product",
    "activity_product",
    "activity_page",
    "custom_page",
}


class QrcodeCreateRequest(BaseModel):
    """创建或复用小程序码请求"""

    model_config = ConfigDict(populate_by_name=True)

    target_type: str = Field(description="目标类型")
    target_key: str = Field(min_length=1, max_length=128, description="目标ID或页面标识")
    title: str = Field(min_length=1, max_length=128, description="二维码标题")
    channel: str = Field(default="default", max_length=64, description="渠道")

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, value: str) -> str:
        if value not in QRCODE_TARGET_TYPES:
            raise ValueError(f"target_type 必须为 {QRCODE_TARGET_TYPES} 之一")
        return value


class QrcodeStatusUpdateRequest(BaseModel):
    """更新二维码状态"""

    status: str = Field(description="状态: active/inactive")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status 必须为 active 或 inactive")
        return value


class QrcodeResponse(BaseModel):
    """小程序码响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    site_id: int
    target_type: str
    target_key: str
    title: str
    path: str
    scene: str
    short_code: str
    channel: str
    image_url: Optional[str] = None
    status: str
    generated_by: Optional[int] = None
    generated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime


class QrcodeResolveResponse(BaseModel):
    """扫码解析响应"""

    qr_code_id: int
    target_type: str
    target_key: str
    title: str
    path: str
    channel: str
    status: str
    attribution_ttl_seconds: int = 86400
