"""
会员相关 Schemas

- AnnualCardInfo / AnnualCardPurchaseRequest / AnnualCardBookingCheck：年卡
- TimesCardInfo / ActivationCodeActivateRequest：次数卡
- PointsInfo / PointsExchangeRequest：积分
"""


import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 年卡配置 ----

class AnnualCardConfigSchema(BaseModel):
    """年卡配置信息（C端展示）"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="配置ID")
    card_name: str = Field(description="卡名称")
    price: Decimal = Field(description="价格")
    duration_days: int = Field(description="有效天数")
    privileges: Dict[str, Any] = Field(default_factory=dict, description="权益说明")
    daily_limit_position: int = Field(description="按位置每日限额")
    daily_limit_quantity: int = Field(description="按人数每日限额")
    max_consecutive_days: int = Field(description="最大连续天数")
    gap_days: int = Field(description="中断天数")
    refund_days: int = Field(description="退款期（天）")
    status: str = Field(description="状态")


# ---- 年卡实例 ----

class AnnualCardInfo(BaseModel):
    """年卡信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="年卡ID")
    user_id: int = Field(description="用户ID")
    config_id: int = Field(description="配置ID")
    order_id: int = Field(description="购买订单ID")
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    real_name: str = Field(description="实名（脱敏）")
    id_card_masked: Optional[str] = Field(default=None, description="身份证号（脱敏）")
    status: str = Field(description="状态: active/expired/refunded")
    created_at: datetime = Field(description="创建时间")

    # 关联
    config_name: Optional[str] = Field(default=None, description="配置名称")
    remaining_days: Optional[int] = Field(default=None, description="剩余天数")

    @field_validator("real_name", mode="before")
    @classmethod
    def mask_name(cls, v: str) -> str:
        """姓名脱敏：保留姓，名用*代替"""
        if v and len(v) >= 2:
            return v[0] + "*" * (len(v) - 1)
        return v


class AnnualCardPurchaseRequest(BaseModel):
    """年卡购买请求"""

    model_config = ConfigDict(populate_by_name=True)

    config_id: int = Field(description="年卡配置ID")
    real_name: str = Field(min_length=1, max_length=50, description="实名")
    id_card: str = Field(description="身份证号")
    payment_method: str = Field(default="wechat_pay", description="支付方式: wechat_pay/mock_pay")

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{17}[\dXx]$", v):
            raise ValueError("身份证号格式不正确")
        return v


class AnnualCardBookingCheck(BaseModel):
    """年卡预定权益校验结果"""

    model_config = ConfigDict(populate_by_name=True)

    can_book: bool = Field(description="是否可以预定")
    reason: Optional[str] = Field(default=None, description="不可预定原因")
    daily_limit_position: int = Field(description="按位置每日限额")
    daily_limit_quantity: int = Field(description="按人数每日限额")
    used_today_position: int = Field(description="今日已用位置名额")
    used_today_quantity: int = Field(description="今日已用人数名额")
    max_consecutive_days: int = Field(description="最大连续天数")
    current_consecutive_days: int = Field(description="当前已连续天数")
    gap_days: int = Field(description="需间隔天数")
    next_available_date: Optional[date] = Field(default=None, description="下次可预定日期")


class AnnualCardBookingRequest(BaseModel):
    """年卡预定营位请求"""

    model_config = ConfigDict(populate_by_name=True)

    annual_card_id: int = Field(description="年卡ID")
    product_id: int = Field(description="商品ID")
    dates: List[date] = Field(min_length=1, description="预定日期列表")
    identity_ids: Optional[List[int]] = Field(default=None, description="出行人身份信息ID列表")


class AnnualCardBookingRecordResponse(BaseModel):
    """年卡预定记录"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="记录ID")
    annual_card_id: int = Field(description="年卡ID")
    booking_date: date = Field(description="预定日期")
    order_id: int = Field(description="订单ID")
    product_id: int = Field(description="商品ID")
    status: str = Field(description="状态: active/cancelled")
    created_at: datetime = Field(description="创建时间")

    # 关联
    product_name: Optional[str] = Field(default=None, description="商品名称")


# ---- 次数卡配置 ----

class TimesCardConfigSchema(BaseModel):
    """次数卡配置信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="配置ID")
    card_name: str = Field(description="卡名称")
    total_times: int = Field(description="总次数")
    validity_days: int = Field(description="有效天数")
    applicable_products: List[int] = Field(default_factory=list, description="适用商品白名单")
    daily_limit: Optional[int] = Field(default=None, description="每日限额")
    status: str = Field(description="状态")


# ---- 次数卡实例 ----

class TimesCardInfo(BaseModel):
    """次数卡信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="次数卡ID")
    user_id: int = Field(description="用户ID")
    config_id: int = Field(description="配置ID")
    total_times: int = Field(description="总次数")
    remaining_times: int = Field(description="剩余次数")
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    activated_at: datetime = Field(description="激活时间")
    status: str = Field(description="状态: active/expired/exhausted")
    created_at: datetime = Field(description="创建时间")

    # 关联
    config_name: Optional[str] = Field(default=None, description="配置名称")
    applicable_products: Optional[List[int]] = Field(default=None, description="适用商品")
    remaining_days: Optional[int] = Field(default=None, description="剩余天数")


class TimesCardCheckResponse(BaseModel):
    """次数卡可用性校验响应"""

    model_config = ConfigDict(populate_by_name=True)

    can_use: bool = Field(description="是否可用")
    reason: Optional[str] = Field(default=None, description="不可用原因")
    remaining_times: int = Field(description="剩余次数")
    consume_count: int = Field(description="本次消耗次数")
    product_applicable: bool = Field(description="商品是否在适用范围")


class TimesCardBookingRequest(BaseModel):
    """次数卡预定营位请求"""

    model_config = ConfigDict(populate_by_name=True)

    times_card_id: int = Field(description="次数卡ID")
    product_id: int = Field(description="商品ID")
    dates: List[date] = Field(min_length=1, description="预定日期列表")
    identity_ids: Optional[List[int]] = Field(default=None, description="出行人身份信息ID列表")


# ---- 激活码 ----

class ActivationCodeActivateRequest(BaseModel):
    """激活码激活请求"""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(
        min_length=16, max_length=16,
        description="16位字母数字激活码",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9]{16}$", v):
            raise ValueError("激活码格式不正确，应为16位字母数字组合")
        return v


class ActivationCodeResponse(BaseModel):
    """激活码信息响应（管理端）"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="激活码ID")
    code: str = Field(description="激活码")
    config_id: int = Field(description="次数卡配置ID")
    status: str = Field(description="状态: unused/used/expired")
    used_by: Optional[int] = Field(default=None, description="使用者")
    used_at: Optional[datetime] = Field(default=None, description="使用时间")
    batch_no: str = Field(description="批次号")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    created_at: datetime = Field(description="创建时间")


class ActivationCodeGenerateRequest(BaseModel):
    """批量生成激活码请求"""

    model_config = ConfigDict(populate_by_name=True)

    config_id: int = Field(description="次数卡配置ID")
    count: int = Field(ge=1, le=1000, description="生成数量（最多1000个）")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class TimesConsumptionRuleSchema(BaseModel):
    """次数消耗规则"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[int] = Field(default=None, description="规则ID")
    config_id: int = Field(description="次数卡配置ID")
    product_id: int = Field(description="商品ID")
    consume_count: int = Field(ge=1, description="每次消耗次数")


# ---- 积分 ----

class PointsInfo(BaseModel):
    """积分信息"""

    model_config = ConfigDict(populate_by_name=True)

    balance: int = Field(description="当前积分余额")
    total_earned: Optional[int] = Field(default=None, description="累计获取")
    total_consumed: Optional[int] = Field(default=None, description="累计消耗")
    expiring_soon: Optional[int] = Field(default=None, description="即将过期积分")
    expiring_date: Optional[date] = Field(default=None, description="最近过期日期")


class PointsRecordResponse(BaseModel):
    """积分变动记录"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="记录ID")
    user_id: int = Field(description="用户ID")
    change_amount: int = Field(description="变动量")
    balance_after: int = Field(description="变动后余额")
    change_type: str = Field(description="变动类型: earn/consume/refund_deduct/expire/manual_adjust")
    reason: Optional[str] = Field(default=None, description="原因")
    order_id: Optional[int] = Field(default=None, description="关联订单ID")
    expires_at: Optional[datetime] = Field(default=None, description="积分过期时间")
    created_at: datetime = Field(description="创建时间")


class PointsExchangeRequest(BaseModel):
    """积分兑换请求"""

    model_config = ConfigDict(populate_by_name=True)

    exchange_config_id: int = Field(description="兑换活动配置ID")
    quantity: int = Field(default=1, ge=1, description="兑换数量")


class PointsExchangeConfigSchema(BaseModel):
    """积分兑换配置"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="配置ID")
    name: str = Field(description="活动名称")
    exchange_type: str = Field(description="兑换类型: free_booking/discount/product")
    product_id: Optional[int] = Field(default=None, description="关联商品ID")
    points_required: int = Field(description="所需积分")
    stock: int = Field(description="库存")
    stock_used: int = Field(description="已兑换数量")
    start_at: datetime = Field(description="开始时间")
    end_at: datetime = Field(description="结束时间")
    status: str = Field(description="状态")

    # 计算字段
    stock_remaining: Optional[int] = Field(default=None, description="剩余库存")


class PointsAdjustRequest(BaseModel):
    """管理端手动调整积分"""

    model_config = ConfigDict(populate_by_name=True)

    change_amount: int = Field(description="调整量（正增负减）")
    reason: str = Field(min_length=1, max_length=200, description="调整原因")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")
