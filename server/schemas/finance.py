"""
财务相关 Schemas

- FinanceAccountInfo：资金账户概览
- WithdrawRequest：提现请求
- TransactionListParams / TransactionResponse：交易流水
- DepositRefundRequest：押金退还
"""


from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 财务账户 ----

class FinanceAccountInfo(BaseModel):
    """财务账户信息概览"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="账户ID")
    pending_amount: Decimal = Field(description="待确认金额")
    available_amount: Decimal = Field(description="可提现金额")
    deposit_amount: Decimal = Field(description="押金专户")
    maintenance_income: Decimal = Field(description="设备维护收入")
    total_income: Decimal = Field(description="累计总收入")

    # 由 Service 层计算填充的聚合字段
    today_income: Optional[Decimal] = Field(default=None, description="今日收入")
    today_refund: Optional[Decimal] = Field(default=None, description="今日退款")
    month_income: Optional[Decimal] = Field(default=None, description="本月收入")
    month_refund: Optional[Decimal] = Field(default=None, description="本月退款")


# ---- 提现 ----

class WithdrawRequest(BaseModel):
    """提现请求"""

    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal = Field(gt=0, description="提现金额")
    bank_account: Optional[str] = Field(default=None, max_length=50, description="银行账户")
    remark: Optional[str] = Field(default=None, max_length=200, description="备注")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("提现金额必须大于0")
        return v


class WithdrawResponse(BaseModel):
    """提现响应"""

    model_config = ConfigDict(populate_by_name=True)

    transaction_no: str = Field(description="交易流水号")
    amount: Decimal = Field(description="提现金额")
    status: str = Field(description="状态")
    created_at: datetime = Field(description="创建时间")


# ---- 交易流水 ----

class TransactionListParams(BaseModel):
    """交易流水查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, description="交易类型: income/refund/deposit_in/deposit_out/deposit_deduct/withdraw")
    account_type: Optional[str] = Field(default=None, description="账户类型: pending/available/deposit/maintenance")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")
    order_id: Optional[int] = Field(default=None, description="关联订单ID")
    min_amount: Optional[Decimal] = Field(default=None, ge=0, description="最小金额")
    max_amount: Optional[Decimal] = Field(default=None, ge=0, description="最大金额")


class TransactionResponse(BaseModel):
    """交易流水响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="流水ID")
    transaction_no: str = Field(description="交易流水号")
    order_id: Optional[int] = Field(default=None, description="关联订单ID")
    type: str = Field(description="交易类型")
    amount: Decimal = Field(description="金额")
    account_type: str = Field(description="账户类型")
    from_account: Optional[str] = Field(default=None, description="转出方")
    to_account: Optional[str] = Field(default=None, description="转入方")
    status: str = Field(description="状态")
    remark: Optional[str] = Field(default=None, description="备注")
    operator_id: Optional[int] = Field(default=None, description="操作人")
    created_at: datetime = Field(description="交易时间")

    # 关联显示
    order_no: Optional[str] = Field(default=None, description="关联订单号")
    operator_name: Optional[str] = Field(default=None, description="操作人姓名")


# ---- 押金 ----

class DepositRecordResponse(BaseModel):
    """押金记录响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="押金记录ID")
    order_id: int = Field(description="订单ID")
    order_item_id: int = Field(description="订单项ID")
    deposit_amount: Decimal = Field(description="押金金额")
    status: str = Field(description="状态: held/returned/deducted/partial_returned")
    return_amount: Optional[Decimal] = Field(default=None, description="退还金额")
    deduct_amount: Optional[Decimal] = Field(default=None, description="扣除金额")
    damage_level: Optional[str] = Field(default=None, description="损坏等级")
    damage_photos: Optional[List[str]] = Field(default=None, description="损坏照片URL")
    damage_remark: Optional[str] = Field(default=None, description="损坏备注")
    processed_by: Optional[int] = Field(default=None, description="处理人ID")
    processed_at: Optional[datetime] = Field(default=None, description="处理时间")
    created_at: datetime = Field(description="创建时间")

    # 关联显示
    order_no: Optional[str] = Field(default=None, description="订单号")
    product_name: Optional[str] = Field(default=None, description="商品名称")
    processor_name: Optional[str] = Field(default=None, description="处理人姓名")


class DepositRefundRequest(BaseModel):
    """押金退还请求"""

    model_config = ConfigDict(populate_by_name=True)

    return_amount: Decimal = Field(ge=0, description="退还金额")
    remark: Optional[str] = Field(default=None, max_length=200, description="备注")


class DepositDeductRequest(BaseModel):
    """押金扣除请求"""

    model_config = ConfigDict(populate_by_name=True)

    damage_level: str = Field(description="损坏等级: minor/moderate/severe/total_loss")
    damage_photos: List[str] = Field(default_factory=list, description="损坏照片URL列表")
    damage_remark: Optional[str] = Field(default=None, max_length=500, description="损坏备注")

    @field_validator("damage_level")
    @classmethod
    def validate_damage_level(cls, v: str) -> str:
        allowed = {"minor", "moderate", "severe", "total_loss"}
        if v not in allowed:
            raise ValueError(f"损坏等级必须为 {allowed} 之一")
        return v


class DamageConfigItem(BaseModel):
    """损坏赔偿配置项"""

    model_config = ConfigDict(populate_by_name=True)

    level: str = Field(description="损坏等级")
    rate: Decimal = Field(ge=0, le=1, description="赔偿比例(0~1)")
    description: Optional[str] = Field(default=None, max_length=200, description="说明")


class DamageConfigUpdate(BaseModel):
    """配置损坏赔偿比例表"""

    model_config = ConfigDict(populate_by_name=True)

    config: List[DamageConfigItem] = Field(min_length=1, description="损坏赔偿配置列表")


# ---- 收入报表 ----

class IncomeReportParams(BaseModel):
    """收入报表查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    granularity: str = Field(default="day", description="粒度: day/week/month")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")
    category: Optional[str] = Field(default=None, description="品类筛选")

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        if v not in ("day", "week", "month"):
            raise ValueError("粒度必须为 day/week/month")
        return v


class IncomeReportItem(BaseModel):
    """收入报表项"""

    model_config = ConfigDict(populate_by_name=True)

    period: str = Field(description="时间段标识（日期/周/月）")
    total_orders: int = Field(description="订单数")
    total_revenue: Decimal = Field(description="总收入")
    refund_amount: Decimal = Field(description="退款金额")
    net_revenue: Decimal = Field(description="净收入")
    avg_order_amount: Optional[Decimal] = Field(default=None, description="平均客单价")
    category_breakdown: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="品类明细 [{category, revenue, orders}]",
    )
