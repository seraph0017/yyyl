"""
商品相关 Schemas

- ProductListItem：商品列表项（精简）
- ProductDetail：商品详情（含扩展、定价、SKU）
- ProductCreate / ProductUpdate：管理端创建/更新
- PricingRuleSchema：定价规则
- SKUSchema：SKU 信息
- InventoryQuery / InventoryResponse：库存查询
- ProductSearchParams：搜索筛选参数
"""

from datetime import date as DateField, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 定价规则 ----

class PricingRuleSchema(BaseModel):
    """定价规则"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[int] = Field(default=None, description="规则ID（更新时传）")
    rule_type: str = Field(description="规则类型: date_type / custom_date")
    date_type: Optional[str] = Field(default=None, description="日期类型: weekday/weekend/holiday")
    custom_date: Optional[DateField] = Field(default=None, description="特定日期")
    price: Decimal = Field(ge=0, description="价格")


class PricingRuleCreate(BaseModel):
    """创建定价规则"""

    model_config = ConfigDict(populate_by_name=True)

    rule_type: str = Field(description="规则类型: date_type / custom_date")
    date_type: Optional[str] = Field(default=None, description="日期类型")
    custom_date: Optional[DateField] = Field(default=None, description="特定日期")
    price: Decimal = Field(ge=0, description="价格")

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in ("date_type", "custom_date"):
            raise ValueError("rule_type 必须为 date_type 或 custom_date")
        return v


# ---- 优惠规则 ----

class DiscountRuleSchema(BaseModel):
    """优惠规则"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[int] = Field(default=None, description="规则ID")
    rule_type: str = Field(description="规则类型: consecutive_days/multi_person/member_discount")
    threshold: int = Field(ge=1, description="阈值")
    discount_rate: Decimal = Field(ge=0, le=1, description="折扣率(0.80=8折)")
    status: str = Field(default="active", description="状态")


class DiscountRuleCreate(BaseModel):
    """创建优惠规则"""

    model_config = ConfigDict(populate_by_name=True)

    rule_type: str = Field(description="规则类型")
    threshold: int = Field(ge=1, description="阈值")
    discount_rate: Decimal = Field(ge=0, le=1, description="折扣率")

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        allowed = {"consecutive_days", "multi_person", "member_discount"}
        if v not in allowed:
            raise ValueError(f"rule_type 必须为 {allowed} 之一")
        return v


# ---- SKU ----

class SKUSchema(BaseModel):
    """SKU 信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="SKU ID")
    product_id: int = Field(description="所属商品ID")
    sku_code: str = Field(description="SKU 编码")
    spec_values: Dict[str, Any] = Field(default_factory=dict, description='规格值 {color:"红",size:"M"}')
    price: Decimal = Field(description="SKU 价格")
    stock: int = Field(description="当前库存")
    status: str = Field(description="状态: active/inactive")
    image_url: Optional[str] = Field(default=None, description="SKU 图片")


class SKUCreate(BaseModel):
    """创建 SKU"""

    model_config = ConfigDict(populate_by_name=True)

    sku_code: str = Field(min_length=1, max_length=50, description="SKU 编码")
    spec_values: Dict[str, Any] = Field(default_factory=dict, description="规格值")
    price: Decimal = Field(ge=0, description="价格")
    stock: int = Field(ge=0, description="库存")
    status: str = Field(default="active", description="状态")
    image_url: Optional[str] = Field(default=None, max_length=512, description="SKU 图片")


class SKUUpdate(BaseModel):
    """更新 SKU"""

    model_config = ConfigDict(populate_by_name=True)

    spec_values: Optional[Dict[str, Any]] = Field(default=None, description="规格值")
    price: Optional[Decimal] = Field(default=None, ge=0, description="价格")
    stock: Optional[int] = Field(default=None, ge=0, description="库存")
    status: Optional[str] = Field(default=None, description="状态")
    image_url: Optional[str] = Field(default=None, max_length=512, description="SKU 图片")


# ---- 扩展表 Schemas ----

class CampingExtSchema(BaseModel):
    """露营票扩展信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    has_electricity: bool = Field(default=False, description="有电")
    has_platform: bool = Field(default=False, description="有木平台")
    sun_exposure: Optional[str] = Field(default=None, description="日照: sunny/shaded/mixed")
    position_name: Optional[str] = Field(default=None, description="营位编号")
    area: Optional[str] = Field(default=None, description="区域")
    max_persons: Optional[int] = Field(default=None, description="最大人数")
    event_start_date: Optional[DateField] = Field(default=None, description="活动起始日")
    event_end_date: Optional[DateField] = Field(default=None, description="活动结束日")


class RentalExtSchema(BaseModel):
    """装备租赁扩展信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    deposit_amount: Decimal = Field(default=Decimal("0"), description="押金")
    rental_category: str = Field(description="租赁分类: overnight/lighting/furniture/vehicle/other")
    damage_config: List[Dict[str, Any]] = Field(default_factory=list, description="损坏配置 [{level,rate}]")


class ActivityExtSchema(BaseModel):
    """活动扩展信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    booking_unit: str = Field(default="person", description="预约单位: person/group")
    time_slots: List[Dict[str, Any]] = Field(default_factory=list, description="场次 [{start,end,capacity}]")
    event_date: Optional[DateField] = Field(default=None, description="特定活动日期")


class ShopExtSchema(BaseModel):
    """商品售卖扩展信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    has_sku: bool = Field(default=False, description="多规格")
    spec_definitions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description='规格定义 [{name:"颜色",values:["红","蓝"]}]',
    )
    shipping_required: bool = Field(default=False, description="需邮寄")
    shop_type: str = Field(default="onsite", description="类型: onsite/online")


# ---- 商品列表/详情 ----

class ProductListItem(BaseModel):
    """商品列表项（精简字段，用于列表展示）"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="商品ID")
    name: str = Field(description="商品名称")
    type: str = Field(description="商品类型")
    booking_mode: Optional[str] = Field(default=None, description="预约模式")
    status: str = Field(description="商品状态")
    base_price: Decimal = Field(description="基础价格")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="商品图片")
    category: Optional[str] = Field(default=None, description="分类")
    sale_start_at: Optional[datetime] = Field(default=None, description="开票时间")
    is_seckill: bool = Field(default=False, description="是否秒杀")
    sort_order: int = Field(default=0, description="排序")
    # 聚合字段（由Service层计算后填充）
    min_price: Optional[Decimal] = Field(default=None, description="最低价（含定价规则）")
    inventory_status: Optional[str] = Field(default=None, description="库存状态概况: available/low/sold_out")


class ProductDetail(BaseModel):
    """商品详情（含扩展属性、定价规则、SKU 列表）"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="商品ID")
    name: str = Field(description="商品名称")
    type: str = Field(description="商品类型")
    booking_mode: Optional[str] = Field(default=None, description="预约模式")
    status: str = Field(description="商品状态")
    base_price: Decimal = Field(description="基础价格")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="商品图片")
    description: Optional[str] = Field(default=None, description="富文本描述")
    category: Optional[str] = Field(default=None, description="分类")
    sale_start_at: Optional[datetime] = Field(default=None, description="开票时间")
    sale_end_at: Optional[datetime] = Field(default=None, description="停售时间")
    refund_deadline_type: str = Field(description="退款截止类型: days/hours")
    refund_deadline_value: int = Field(description="提前N天/小时可退")
    require_disclaimer: bool = Field(description="需签免责声明")
    require_camping_ticket: bool = Field(description="需先购露营票")
    is_seckill: bool = Field(description="是否秒杀")
    seckill_payment_timeout: int = Field(description="秒杀支付超时(秒)")
    normal_payment_timeout: int = Field(description="普通支付超时(秒)")
    sort_order: int = Field(description="排序")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    # 扩展信息（根据 type 只有一个不为 None）
    ext_camping: Optional[CampingExtSchema] = Field(default=None, description="露营票扩展")
    ext_rental: Optional[RentalExtSchema] = Field(default=None, description="装备租赁扩展")
    ext_activity: Optional[ActivityExtSchema] = Field(default=None, description="活动扩展")
    ext_shop: Optional[ShopExtSchema] = Field(default=None, description="商品售卖扩展")

    # 关联列表
    pricing_rules: List[PricingRuleSchema] = Field(default_factory=list, description="定价规则列表")
    discount_rules: List[DiscountRuleSchema] = Field(default_factory=list, description="优惠规则列表")
    skus: List[SKUSchema] = Field(default_factory=list, description="SKU 列表")


# ---- 商品创建/更新 ----

class ProductCreate(BaseModel):
    """创建商品（管理端）"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=100, description="商品名称")
    type: str = Field(description="商品类型")
    booking_mode: Optional[str] = Field(default=None, description="预约模式: by_position/by_quantity")
    base_price: Decimal = Field(ge=0, description="基础价格")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="商品图片 [{url, sort_order}]")
    description: Optional[str] = Field(default=None, description="富文本描述")
    category: Optional[str] = Field(default=None, max_length=50, description="分类")
    sale_start_at: Optional[datetime] = Field(default=None, description="开票时间")
    sale_end_at: Optional[datetime] = Field(default=None, description="停售时间")
    refund_deadline_type: str = Field(default="hours", description="退款截止类型")
    refund_deadline_value: int = Field(default=24, ge=0, description="提前可退数值")
    require_disclaimer: bool = Field(default=True, description="需签免责声明")
    require_camping_ticket: bool = Field(default=False, description="需先购露营票")
    is_seckill: bool = Field(default=False, description="是否秒杀")
    seckill_payment_timeout: int = Field(default=300, ge=60, description="秒杀超时(秒)")
    normal_payment_timeout: int = Field(default=1800, ge=60, description="普通超时(秒)")
    sort_order: int = Field(default=0, ge=0, description="排序")

    # 扩展信息（根据 type 传对应的）
    ext_camping: Optional[CampingExtSchema] = Field(default=None, description="露营票扩展")
    ext_rental: Optional[RentalExtSchema] = Field(default=None, description="装备租赁扩展")
    ext_activity: Optional[ActivityExtSchema] = Field(default=None, description="活动扩展")
    ext_shop: Optional[ShopExtSchema] = Field(default=None, description="商品售卖扩展")

    # SKU（创建时可一起传入）
    skus: List[SKUCreate] = Field(default_factory=list, description="SKU 列表")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {
            "daily_camping", "event_camping", "rental",
            "daily_activity", "special_activity", "shop", "merchandise",
        }
        if v not in allowed:
            raise ValueError(f"商品类型必须为 {allowed} 之一")
        return v


class ProductUpdate(BaseModel):
    """更新商品（管理端，所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=100, description="商品名称")
    booking_mode: Optional[str] = Field(default=None, description="预约模式")
    status: Optional[str] = Field(default=None, description="商品状态")
    base_price: Optional[Decimal] = Field(default=None, ge=0, description="基础价格")
    images: Optional[List[Dict[str, Any]]] = Field(default=None, description="商品图片")
    description: Optional[str] = Field(default=None, description="富文本描述")
    category: Optional[str] = Field(default=None, max_length=50, description="分类")
    sale_start_at: Optional[datetime] = Field(default=None, description="开票时间")
    sale_end_at: Optional[datetime] = Field(default=None, description="停售时间")
    refund_deadline_type: Optional[str] = Field(default=None, description="退款截止类型")
    refund_deadline_value: Optional[int] = Field(default=None, ge=0, description="提前可退数值")
    require_disclaimer: Optional[bool] = Field(default=None, description="需签免责声明")
    require_camping_ticket: Optional[bool] = Field(default=None, description="需先购露营票")
    is_seckill: Optional[bool] = Field(default=None, description="是否秒杀")
    seckill_payment_timeout: Optional[int] = Field(default=None, ge=60, description="秒杀超时(秒)")
    normal_payment_timeout: Optional[int] = Field(default=None, ge=60, description="普通超时(秒)")
    sort_order: Optional[int] = Field(default=None, ge=0, description="排序")

    # 扩展信息
    ext_camping: Optional[CampingExtSchema] = Field(default=None, description="露营票扩展")
    ext_rental: Optional[RentalExtSchema] = Field(default=None, description="装备租赁扩展")
    ext_activity: Optional[ActivityExtSchema] = Field(default=None, description="活动扩展")
    ext_shop: Optional[ShopExtSchema] = Field(default=None, description="商品售卖扩展")


class ProductStatusUpdate(BaseModel):
    """商品上架/下架"""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(description="目标状态: on_sale / off_sale")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("on_sale", "off_sale"):
            raise ValueError("状态必须为 on_sale 或 off_sale")
        return v


class BatchStatusUpdate(BaseModel):
    """批量上架/下架"""

    model_config = ConfigDict(populate_by_name=True)

    product_ids: List[int] = Field(min_length=1, description="商品ID列表")
    status: str = Field(description="目标状态: on_sale / off_sale")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


class BatchPricingUpdate(BaseModel):
    """批量修改价格"""

    model_config = ConfigDict(populate_by_name=True)

    product_ids: List[int] = Field(min_length=1, description="商品ID列表")
    price_adjustment: Decimal = Field(description="价格调整量（正增负减）")
    adjustment_type: str = Field(description="调整方式: absolute(绝对值) / percentage(百分比)")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


# ---- 库存查询 ----

class InventoryQuery(BaseModel):
    """库存查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: Optional[int] = Field(default=None, description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    date_start: Optional[DateField] = Field(default=None, description="起始日期")
    date_end: Optional[DateField] = Field(default=None, description="结束日期")
    status: Optional[str] = Field(default=None, description="库存状态: open/closed")


class InventoryResponse(BaseModel):
    """库存信息响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="库存记录ID")
    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    date: Optional[DateField] = Field(default=None, description="日期")
    time_slot: Optional[str] = Field(default=None, description="场次")
    total: int = Field(description="总库存")
    available: int = Field(description="可用")
    locked: int = Field(description="锁定中")
    sold: int = Field(description="已售")
    status: str = Field(description="状态")
    created_at: datetime = Field(description="创建时间")


class InventoryUpdate(BaseModel):
    """更新库存"""

    model_config = ConfigDict(populate_by_name=True)

    total: Optional[int] = Field(default=None, ge=0, description="总库存")
    status: Optional[str] = Field(default=None, description="状态: open/closed")
    remark: Optional[str] = Field(default=None, max_length=200, description="操作备注")


class BatchInventoryUpdate(BaseModel):
    """批量调整库存"""

    model_config = ConfigDict(populate_by_name=True)

    inventory_ids: List[int] = Field(min_length=1, description="库存记录ID列表")
    total: Optional[int] = Field(default=None, ge=0, description="设置总库存")
    status: Optional[str] = Field(default=None, description="状态")
    remark: Optional[str] = Field(default=None, max_length=200, description="操作备注")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


class BatchInventoryOpen(BaseModel):
    """批量开启库存"""

    model_config = ConfigDict(populate_by_name=True)

    product_ids: List[int] = Field(min_length=1, description="商品ID列表")
    date_start: DateField = Field(description="起始日期")
    date_end: DateField = Field(description="结束日期")
    total_per_day: int = Field(ge=1, description="每日库存总量")
    remark: Optional[str] = Field(default=None, max_length=200, description="备注")


class InventoryLogResponse(BaseModel):
    """库存变动日志"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="日志ID")
    inventory_id: int = Field(description="库存ID")
    change_type: str = Field(description="变动类型")
    quantity: int = Field(description="变动量")
    order_id: Optional[int] = Field(default=None, description="关联订单")
    operator_id: Optional[int] = Field(default=None, description="操作人")
    remark: Optional[str] = Field(default=None, description="备注")
    created_at: datetime = Field(description="变动时间")


# ---- 价格日历 ----

class PriceCalendarItem(BaseModel):
    """价格日历项"""

    model_config = ConfigDict(populate_by_name=True)

    date: DateField = Field(description="日期")
    date_type: str = Field(description="日期类型: weekday/weekend/holiday/custom")
    price: Decimal = Field(description="价格")
    available: int = Field(description="可用库存")
    status: str = Field(description="库存状态: open/closed")


# ---- 商品搜索/筛选 ----

class ProductSearchParams(BaseModel):
    """商品搜索/筛选参数"""

    model_config = ConfigDict(populate_by_name=True)

    keyword: Optional[str] = Field(default=None, max_length=50, description="搜索关键词")
    type: Optional[str] = Field(default=None, description="商品类型")
    category: Optional[str] = Field(default=None, description="分类")
    status: Optional[str] = Field(default=None, description="商品状态")
    min_price: Optional[Decimal] = Field(default=None, ge=0, description="最低价")
    max_price: Optional[Decimal] = Field(default=None, ge=0, description="最高价")
    date: Optional[DateField] = Field(default=None, description="可预约日期")
    is_seckill: Optional[bool] = Field(default=None, description="是否秒杀")


# ---- 日期类型配置 ----

class DateTypeConfigSchema(BaseModel):
    """日期类型配置"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="配置ID")
    date: DateField = Field(description="日期")
    date_type: str = Field(description="日期类型")
    label: Optional[str] = Field(default=None, description="标签")


class DateTypeConfigItem(BaseModel):
    """日期类型配置项"""

    model_config = ConfigDict(populate_by_name=True)

    date: DateField = Field(description="日期")
    date_type: str = Field(description="日期类型: weekday/weekend/holiday/custom")
    label: Optional[str] = Field(default=None, max_length=30, description="标签")

    @field_validator("date_type")
    @classmethod
    def validate_date_type(cls, v: str) -> str:
        allowed = {"weekday", "weekend", "holiday", "custom"}
        if v not in allowed:
            raise ValueError(f"日期类型必须为 {allowed} 之一")
        return v


class DateTypeConfigUpdate(BaseModel):
    """批量设置日期类型"""

    model_config = ConfigDict(populate_by_name=True)

    items: List[DateTypeConfigItem] = Field(min_length=1, description="日期类型列表")
