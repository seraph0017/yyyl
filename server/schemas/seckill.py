"""
秒杀增强相关 Schemas

- SeckillPrefillSave / SeckillPrefillResponse：秒杀预填数据
- SeckillStatusResponse：秒杀实时状态（C端）
- SeckillMonitorResponse：秒杀监控数据（B端）
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 秒杀预填数据 ----

class SeckillPrefillSave(BaseModel):
    """保存秒杀预填数据"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="秒杀商品ID")
    identity_ids: List[int] = Field(
        default_factory=list, description="出行人身份信息ID列表",
    )
    phone: Optional[str] = Field(
        default=None, max_length=20, description="联系电话",
    )
    disclaimer_signed: bool = Field(default=False, description="是否已签署免责声明")
    bundle_items: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="搭配商品项（可选）",
    )


class SeckillPrefillResponse(BaseModel):
    """秒杀预填数据响应"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="秒杀商品ID")
    identity_ids: List[int] = Field(
        default_factory=list, description="出行人身份信息ID列表",
    )
    phone: Optional[str] = Field(default=None, description="联系电话")
    disclaimer_signed: bool = Field(default=False, description="是否已签署免责声明")
    bundle_items: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="搭配商品项",
    )
    saved_at: Optional[datetime] = Field(default=None, description="保存时间")


# ---- 秒杀实时状态（C端） ----

class SeckillStatusResponse(BaseModel):
    """秒杀实时状态响应"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="秒杀商品ID")
    remaining_stock: int = Field(description="剩余库存")
    online_count: int = Field(description="在线人数")
    status: str = Field(description="秒杀状态: warmup/active/sold_out/ended")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"warmup", "active", "sold_out", "ended"}
        if v not in allowed:
            raise ValueError(f"秒杀状态必须为 {allowed} 之一")
        return v


# ---- 秒杀监控数据（B端） ----

class SeckillMonitorResponse(BaseModel):
    """秒杀监控数据响应"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="秒杀商品ID")
    online_count: int = Field(description="当前在线人数")
    remaining_stock: int = Field(description="剩余库存")
    orders_created: int = Field(description="已创建订单数")
    orders_paid: int = Field(description="已支付订单数")
    peak_qps: int = Field(description="峰值QPS")
