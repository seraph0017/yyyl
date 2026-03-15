"""
绩效统计相关 Schemas

- PerformanceConfigUpdate / PerformanceConfigItem / PerformanceConfigResponse：绩效系数配置
- PerformanceRecordResponse / PerformanceDetailResponse：绩效记录
- PerformanceRankingItem：绩效排名
- PerformanceCalculateRequest：绩效计算请求
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 绩效系数配置 ----

class PerformanceConfigItem(BaseModel):
    """单条绩效系数配置项"""

    model_config = ConfigDict(populate_by_name=True)

    income_type: str = Field(description="收入类型: campsite/rental/shop/activity/membership")
    coefficient: Decimal = Field(
        ge=0, le=Decimal("1.0000"),
        description="绩效系数（如0.0300=3%）",
    )
    description: Optional[str] = Field(default=None, description="说明")

    @field_validator("income_type")
    @classmethod
    def validate_income_type(cls, v: str) -> str:
        allowed = {"campsite", "rental", "shop", "activity", "membership"}
        if v not in allowed:
            raise ValueError(f"收入类型必须为 {allowed} 之一")
        return v


class PerformanceConfigUpdate(BaseModel):
    """批量更新绩效系数配置"""

    model_config = ConfigDict(populate_by_name=True)

    configs: List[PerformanceConfigItem] = Field(
        min_length=1, description="绩效系数配置列表",
    )


class PerformanceConfigResponse(BaseModel):
    """绩效系数配置响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="配置ID")
    income_type: str = Field(description="收入类型")
    coefficient: Decimal = Field(description="绩效系数")
    description: Optional[str] = Field(default=None, description="说明")
    site_id: int = Field(description="营地ID")


# ---- 绩效记录 ----

class PerformanceDetailResponse(BaseModel):
    """绩效分项明细响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    income_type: str = Field(description="收入类型")
    income_amount: Decimal = Field(description="该类型收入金额")
    performance_amount: Decimal = Field(description="该类型绩效金额")


class PerformanceRecordResponse(BaseModel):
    """绩效汇总记录响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="记录ID")
    staff_user_id: int = Field(description="员工管理员ID")
    staff_name: Optional[str] = Field(default=None, description="员工姓名")
    period_type: str = Field(description="周期类型: daily/weekly/monthly")
    period_start: date = Field(description="周期开始日期")
    period_end: date = Field(description="周期结束日期")
    total_income: Decimal = Field(description="总收入")
    total_performance: Decimal = Field(description="总绩效")
    site_id: int = Field(description="营地ID")
    created_at: datetime = Field(description="创建时间")

    # 关联
    details: List[PerformanceDetailResponse] = Field(
        default_factory=list, description="绩效分项明细列表",
    )


# ---- 绩效排名 ----

class PerformanceRankingItem(BaseModel):
    """绩效排名项"""

    model_config = ConfigDict(populate_by_name=True)

    rank: int = Field(description="排名")
    staff_user_id: int = Field(description="员工管理员ID")
    staff_name: str = Field(description="员工姓名")
    total_performance: Decimal = Field(description="总绩效")
    total_income: Decimal = Field(description="总收入")


# ---- 绩效计算请求 ----

class PerformanceCalculateRequest(BaseModel):
    """绩效计算请求"""

    model_config = ConfigDict(populate_by_name=True)

    period_type: str = Field(description="周期类型: daily/weekly/monthly")
    period_start: date = Field(description="周期开始日期")
    period_end: Optional[date] = Field(
        default=None,
        description="周期结束日期（daily 可省略，自动设为 period_start）",
    )

    @field_validator("period_type")
    @classmethod
    def validate_period_type(cls, v: str) -> str:
        if v not in ("daily", "weekly", "monthly"):
            raise ValueError("周期类型必须为 daily/weekly/monthly")
        return v
