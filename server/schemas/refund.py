"""
v1.7 退款 Schema
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RefundCreateItem(BaseModel):
    """按项退款明细"""

    model_config = ConfigDict(populate_by_name=True)

    order_item_id: int = Field(description="订单项ID")
    refund_amount: Decimal = Field(gt=0, description="退款金额")
    quantity: int = Field(default=1, ge=1, description="数量")


class RefundCreateRequest(BaseModel):
    """创建退款请求"""

    model_config = ConfigDict(populate_by_name=True)

    refund_mode: str = Field(description="退款模式: full/partial/item")
    order_action: str = Field(description="订单处理: keep_order/cancel_order")
    refund_amount: Decimal = Field(gt=0, description="退款金额")
    release_inventory: bool = Field(default=True, description="是否释放库存")
    reason: str = Field(min_length=1, max_length=500, description="退款原因")
    items: Optional[List[RefundCreateItem]] = Field(default=None, description="退款明细")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")
    operation_password: Optional[str] = Field(default=None, description="操作密码")

    @field_validator("refund_mode")
    @classmethod
    def validate_refund_mode(cls, value: str) -> str:
        if value not in {"full", "partial", "item"}:
            raise ValueError("refund_mode 必须为 full/partial/item")
        return value

    @field_validator("order_action")
    @classmethod
    def validate_order_action(cls, value: str) -> str:
        if value not in {"keep_order", "cancel_order"}:
            raise ValueError("order_action 必须为 keep_order/cancel_order")
        return value

    @model_validator(mode="after")
    def validate_items_for_item_mode(self) -> "RefundCreateRequest":
        if self.refund_mode == "item" and not self.items:
            raise ValueError("item 模式必须提供退款明细")
        return self


class RefundRejectRequest(BaseModel):
    """拒绝退款请求"""

    reason: str = Field(min_length=1, max_length=500, description="拒绝原因")


class RefundApproveRequest(BaseModel):
    """审批退款请求"""

    confirm_code: Optional[str] = Field(default=None, description="二次确认码")
    operation_password: Optional[str] = Field(default=None, description="操作密码")


class RefundRecordResponse(BaseModel):
    """退款记录响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    site_id: int
    order_id: int
    refund_no: str
    refund_mode: str
    order_action: str
    refund_amount: Decimal
    system_amount: Decimal
    release_inventory: bool
    reason: str
    risk_level: str
    status: str
    wechat_refund_id: Optional[str] = None
    requested_by: int
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
