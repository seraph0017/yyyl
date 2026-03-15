"""
搭配售卖相关 Schemas

- BundleConfigCreate / BundleConfigUpdate：搭配组合管理
- BundleConfigResponse / BundleItemResponse：搭配组合响应
- BundleRecommendItem：C端搭配推荐项
- BundleStatsResponse：搭配统计
- InsuranceExtCreate / InsuranceExtResponse：保险扩展
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 搭配项 ----

class BundleItemCreate(BaseModel):
    """创建搭配商品项"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="搭配商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID（多规格商品）")
    bundle_price: Optional[Decimal] = Field(
        default=None, ge=0, description="搭配优惠价（NULL则使用商品原价）",
    )
    max_quantity: int = Field(default=1, ge=1, le=99, description="最大可选数量")
    is_default_checked: bool = Field(default=False, description="是否默认勾选")
    sort_order: int = Field(default=0, ge=0, description="排序")


class BundleItemResponse(BaseModel):
    """搭配商品项响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="搭配项ID")
    product_id: int = Field(description="搭配商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    bundle_price: Optional[Decimal] = Field(default=None, description="搭配优惠价")
    max_quantity: int = Field(description="最大可选数量")
    is_default_checked: bool = Field(description="是否默认勾选")
    sort_order: int = Field(default=0, description="排序")

    # 关联显示字段（由 Service 层填充）
    product_name: Optional[str] = Field(default=None, description="商品名称")
    product_image: Optional[str] = Field(default=None, description="商品首图")


# ---- 搭配组合配置 ----

class BundleConfigCreate(BaseModel):
    """创建搭配组合配置"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=100, description="组合名称")
    main_product_id: int = Field(description="主商品ID")
    status: str = Field(default="active", description="状态: active/inactive")
    start_at: Optional[datetime] = Field(default=None, description="生效起始时间")
    end_at: Optional[datetime] = Field(default=None, description="生效结束时间")
    sort_order: int = Field(default=0, ge=0, description="排序")
    items: List[BundleItemCreate] = Field(
        min_length=1, description="搭配商品项列表（至少1项）",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("active", "inactive"):
            raise ValueError("状态必须为 active 或 inactive")
        return v


class BundleConfigUpdate(BaseModel):
    """更新搭配组合配置（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=100, description="组合名称")
    status: Optional[str] = Field(default=None, description="状态: active/inactive")
    start_at: Optional[datetime] = Field(default=None, description="生效起始时间")
    end_at: Optional[datetime] = Field(default=None, description="生效结束时间")
    sort_order: Optional[int] = Field(default=None, ge=0, description="排序")
    items: Optional[List[BundleItemCreate]] = Field(
        default=None, description="搭配商品项列表（传入则全量替换）",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "inactive"):
            raise ValueError("状态必须为 active 或 inactive")
        return v


class BundleConfigResponse(BaseModel):
    """搭配组合配置响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="搭配组合ID")
    main_product_id: int = Field(description="主商品ID")
    name: str = Field(description="组合名称")
    status: str = Field(description="状态")
    start_at: Optional[datetime] = Field(default=None, description="生效起始时间")
    end_at: Optional[datetime] = Field(default=None, description="生效结束时间")
    sort_order: int = Field(default=0, description="排序")
    site_id: int = Field(description="营地ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    # 关联
    items: List[BundleItemResponse] = Field(
        default_factory=list, description="搭配商品项列表",
    )


# ---- C端搭配推荐 ----

class BundleRecommendItem(BaseModel):
    """C端搭配推荐商品项"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    product_name: str = Field(description="商品名称")
    product_image: Optional[str] = Field(default=None, description="商品首图")
    original_price: Decimal = Field(description="商品原价")
    bundle_price: Optional[Decimal] = Field(default=None, description="搭配优惠价")
    max_quantity: int = Field(description="最大可选数量")
    is_default_checked: bool = Field(description="是否默认勾选")


# ---- 搭配统计 ----

class BundleTopItem(BaseModel):
    """搭配TOP商品项"""

    model_config = ConfigDict(populate_by_name=True)

    bundle_config_id: int = Field(description="搭配组合ID")
    bundle_name: str = Field(description="组合名称")
    order_count: int = Field(description="关联订单数")
    revenue: Decimal = Field(description="搭配收入")


class BundleStatsResponse(BaseModel):
    """搭配统计响应"""

    model_config = ConfigDict(populate_by_name=True)

    total_bundle_orders: int = Field(description="搭配订单总数")
    bundle_rate: Decimal = Field(description="搭配率（%）")
    bundle_revenue: Decimal = Field(description="搭配总收入")
    top_bundles: List[BundleTopItem] = Field(
        default_factory=list, description="TOP搭配组合列表",
    )


# ---- 保险扩展 ----

class InsuranceExtCreate(BaseModel):
    """创建保险产品扩展"""

    model_config = ConfigDict(populate_by_name=True)

    insurer: str = Field(min_length=1, max_length=100, description="承保机构")
    coverage_content: str = Field(min_length=1, description="保障内容（富文本）")
    coverage_days: int = Field(ge=1, description="保障天数")
    claim_phone: Optional[str] = Field(
        default=None, max_length=20, description="理赔电话",
    )
    terms_url: Optional[str] = Field(
        default=None, max_length=500, description="保险条款链接",
    )
    age_min: Optional[int] = Field(default=None, ge=0, description="最小投保年龄")
    age_max: Optional[int] = Field(default=None, ge=0, description="最大投保年龄")
    claim_process: Optional[str] = Field(default=None, description="理赔流程说明")
    license_no: Optional[str] = Field(
        default=None, max_length=100, description="保险许可证号",
    )

    @field_validator("age_max")
    @classmethod
    def validate_age_range(cls, v: Optional[int], info) -> Optional[int]:
        age_min = info.data.get("age_min")
        if v is not None and age_min is not None and v < age_min:
            raise ValueError("最大投保年龄不能小于最小投保年龄")
        return v


class InsuranceExtResponse(BaseModel):
    """保险产品扩展响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="扩展ID")
    product_id: int = Field(description="商品ID")
    insurer: str = Field(description="承保机构")
    coverage_content: str = Field(description="保障内容")
    coverage_days: int = Field(description="保障天数")
    claim_phone: Optional[str] = Field(default=None, description="理赔电话")
    terms_url: Optional[str] = Field(default=None, description="保险条款链接")
    age_min: Optional[int] = Field(default=None, description="最小投保年龄")
    age_max: Optional[int] = Field(default=None, description="最大投保年龄")
    claim_process: Optional[str] = Field(default=None, description="理赔流程说明")
    license_no: Optional[str] = Field(default=None, description="保险许可证号")
