"""
报销系统相关 Schemas

- ExpenseTypeCreate / ExpenseTypeUpdate / ExpenseTypeResponse：报销类型
- ExpenseRequestCreate / ExpenseRequestResponse：报销申请
- ExpenseApproveRequest：审批请求
- ExpenseStatsResponse：报销统计
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 报销类型 ----

class ExpenseTypeCreate(BaseModel):
    """创建报销类型"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=50, description="类型名称")
    description: Optional[str] = Field(default=None, description="类型描述")
    sort_order: int = Field(default=0, ge=0, description="排序")


class ExpenseTypeUpdate(BaseModel):
    """更新报销类型（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=50, description="类型名称")
    description: Optional[str] = Field(default=None, description="类型描述")
    status: Optional[str] = Field(default=None, description="状态: active/inactive")
    sort_order: Optional[int] = Field(default=None, ge=0, description="排序")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "inactive"):
            raise ValueError("状态必须为 active 或 inactive")
        return v


class ExpenseTypeResponse(BaseModel):
    """报销类型响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="类型ID")
    name: str = Field(description="类型名称")
    description: Optional[str] = Field(default=None, description="类型描述")
    status: str = Field(description="状态")
    sort_order: int = Field(default=0, description="排序")
    site_id: int = Field(description="营地ID")


# ---- 报销申请 ----

class ExpenseRequestCreate(BaseModel):
    """创建报销申请"""

    model_config = ConfigDict(populate_by_name=True)

    expense_type_id: int = Field(description="报销类型ID")
    amount: Decimal = Field(gt=0, le=Decimal("999999.99"), description="报销金额")
    expense_date: date = Field(description="费用发生日期")
    description: Optional[str] = Field(default=None, description="报销说明")
    receipt_images: List[str] = Field(
        min_length=1, description="凭证图片URL列表（至少1张）",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("报销金额必须大于0")
        return v


class ExpenseRequestResponse(BaseModel):
    """报销申请响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="报销申请ID")
    user_id: int = Field(description="报销人ID")
    created_by: Optional[int] = Field(default=None, description="代提交人ID")
    expense_type_id: int = Field(description="报销类型ID")
    amount: Decimal = Field(description="报销金额")
    expense_date: date = Field(description="费用发生日期")
    description: Optional[str] = Field(default=None, description="报销说明")
    receipt_images: List[str] = Field(
        default_factory=list, description="凭证图片URL列表",
    )
    status: str = Field(description="状态: pending/approved/rejected/paid")
    reviewer_id: Optional[int] = Field(default=None, description="审批人ID")
    reviewed_at: Optional[datetime] = Field(default=None, description="审批时间")
    review_remark: Optional[str] = Field(default=None, description="审批备注")
    paid_at: Optional[datetime] = Field(default=None, description="打款时间")
    paid_by: Optional[int] = Field(default=None, description="打款操作人")
    site_id: int = Field(description="营地ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    # 关联显示字段（由 Service 层填充）
    applicant_name: Optional[str] = Field(default=None, description="报销人姓名")
    expense_type_name: Optional[str] = Field(default=None, description="报销类型名称")


# ---- 报销审批 ----

class ExpenseApproveRequest(BaseModel):
    """审批报销请求"""

    model_config = ConfigDict(populate_by_name=True)

    approved: bool = Field(description="是否通过")
    review_remark: Optional[str] = Field(
        default=None, max_length=500, description="审批备注",
    )


# ---- 报销统计 ----

class ExpenseTypeBreakdown(BaseModel):
    """按报销类型统计"""

    model_config = ConfigDict(populate_by_name=True)

    expense_type_id: int = Field(description="报销类型ID")
    expense_type_name: str = Field(description="报销类型名称")
    total_amount: Decimal = Field(description="总金额")
    count: int = Field(description="申请数")


class ExpenseStaffBreakdown(BaseModel):
    """按员工统计"""

    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(description="员工ID")
    staff_name: str = Field(description="员工姓名")
    total_amount: Decimal = Field(description="总金额")
    count: int = Field(description="申请数")


class ExpenseStatsResponse(BaseModel):
    """报销统计响应"""

    model_config = ConfigDict(populate_by_name=True)

    total_amount: Decimal = Field(description="总金额")
    month_total: Decimal = Field(description="当月总金额")
    type_breakdown: List[ExpenseTypeBreakdown] = Field(
        default_factory=list, description="按类型统计",
    )
    staff_breakdown: List[ExpenseStaffBreakdown] = Field(
        default_factory=list, description="按员工统计",
    )
