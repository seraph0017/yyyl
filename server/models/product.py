"""
商品相关模型
- Product（商品基础表）
- ProductExtCamping（露营票扩展表）
- ProductExtRental（装备租赁扩展表）
- ProductExtActivity（活动扩展表）
- ProductExtShop（商品售卖扩展表）
- SKU（库存最小单位表）
- PricingRule（定价规则表）
- DateTypeConfig（日期类型配置表）
- DiscountRule（优惠规则表）
- Inventory（库存表）
- InventoryLog（库存变动日志）
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.order import CartItem, OrderItem


# ---- 枚举类型 ----

class ProductType(str, enum.Enum):
    DAILY_CAMPING = "daily_camping"
    EVENT_CAMPING = "event_camping"
    RENTAL = "rental"
    DAILY_ACTIVITY = "daily_activity"
    SPECIAL_ACTIVITY = "special_activity"
    SHOP = "shop"
    MERCHANDISE = "merchandise"


class BookingMode(str, enum.Enum):
    BY_POSITION = "by_position"  # 孤品
    BY_QUANTITY = "by_quantity"  # 通品


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ON_SALE = "on_sale"
    OFF_SALE = "off_sale"


class RefundDeadlineType(str, enum.Enum):
    DAYS = "days"
    HOURS = "hours"


class SunExposure(str, enum.Enum):
    SUNNY = "sunny"
    SHADED = "shaded"
    MIXED = "mixed"


class RentalCategory(str, enum.Enum):
    OVERNIGHT = "overnight"
    LIGHTING = "lighting"
    FURNITURE = "furniture"
    VEHICLE = "vehicle"
    OTHER = "other"


class BookingUnit(str, enum.Enum):
    PERSON = "person"
    GROUP = "group"


class ShopType(str, enum.Enum):
    ONSITE = "onsite"
    ONLINE = "online"


class PricingRuleType(str, enum.Enum):
    DATE_TYPE = "date_type"
    CUSTOM_DATE = "custom_date"


class DateType(str, enum.Enum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    CUSTOM = "custom"


class DiscountRuleType(str, enum.Enum):
    CONSECUTIVE_DAYS = "consecutive_days"
    MULTI_PERSON = "multi_person"
    MEMBER_DISCOUNT = "member_discount"


class SKUStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class InventoryStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class InventoryChangeType(str, enum.Enum):
    LOCK = "lock"
    UNLOCK = "unlock"
    SELL = "sell"
    REFUND = "refund"
    RESTOCK = "restock"
    MANUAL_ADJUST = "manual_adjust"


# ---- 模型 ----

class Product(Base):
    """商品基础表"""

    __tablename__ = "product"
    __table_args__ = (
        Index("idx_product_type_status", "type", "status"),
        Index("idx_product_site", "site_id", "type"),
        Index("idx_product_sale_start", "sale_start_at"),
        {"comment": "商品基础表"},
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="商品名称"
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="商品类型: daily_camping/event_camping/rental/daily_activity/special_activity/shop/merchandise"
    )
    booking_mode: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="预约模式: by_position(孤品)/by_quantity(通品)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProductStatus.DRAFT.value,
        server_default=ProductStatus.DRAFT.value,
        comment="商品状态: draft/on_sale/off_sale"
    )
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="基础价格（兜底）"
    )
    images: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]",
        comment="商品图片 [{url, sort_order}]"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="富文本描述"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="分类"
    )
    sale_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="定时开票时间"
    )
    sale_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="停售时间"
    )
    refund_deadline_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default=RefundDeadlineType.HOURS.value,
        server_default=RefundDeadlineType.HOURS.value,
        comment="退款截止类型: days/hours"
    )
    refund_deadline_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24, server_default="24",
        comment="提前N天/小时可退"
    )
    require_disclaimer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
        comment="需签免责声明"
    )
    require_camping_ticket: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="需先购露营票"
    )
    is_seckill: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="秒杀模式"
    )
    seckill_payment_timeout: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300",
        comment="秒杀支付超时(秒)"
    )
    normal_payment_timeout: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1800, server_default="1800",
        comment="普通支付超时(秒)"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    ext_camping: Mapped[Optional["ProductExtCamping"]] = relationship(
        back_populates="product", uselist=False, lazy="selectin"
    )
    ext_rental: Mapped[Optional["ProductExtRental"]] = relationship(
        back_populates="product", uselist=False, lazy="selectin"
    )
    ext_activity: Mapped[Optional["ProductExtActivity"]] = relationship(
        back_populates="product", uselist=False, lazy="selectin"
    )
    ext_shop: Mapped[Optional["ProductExtShop"]] = relationship(
        back_populates="product", uselist=False, lazy="selectin"
    )
    skus: Mapped[List["SKU"]] = relationship(
        back_populates="product", lazy="selectin"
    )
    pricing_rules: Mapped[List["PricingRule"]] = relationship(
        back_populates="product", lazy="noload"
    )
    discount_rules: Mapped[List["DiscountRule"]] = relationship(
        back_populates="product", lazy="noload"
    )
    inventories: Mapped[List["Inventory"]] = relationship(
        back_populates="product", lazy="noload"
    )


class ProductExtCamping(Base):
    """露营票扩展表"""

    __tablename__ = "product_ext_camping"
    __table_args__ = {"comment": "露营票扩展表"}

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), unique=True, nullable=False, comment="商品ID"
    )
    has_electricity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="有电"
    )
    has_platform: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="有木平台"
    )
    sun_exposure: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="日照: sunny/shaded/mixed"
    )
    position_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="营位编号"
    )
    area: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="区域"
    )
    max_persons: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="最大人数"
    )
    event_start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="活动起始日"
    )
    event_end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="活动结束日"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="ext_camping")


class ProductExtRental(Base):
    """装备租赁扩展表"""

    __tablename__ = "product_ext_rental"
    __table_args__ = {"comment": "装备租赁扩展表"}

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), unique=True, nullable=False, comment="商品ID"
    )
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="押金"
    )
    rental_category: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="租赁分类: overnight/lighting/furniture/vehicle/other"
    )
    damage_config: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]",
        comment="损坏配置 [{level,rate}]"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="ext_rental")


class ProductExtActivity(Base):
    """活动扩展表"""

    __tablename__ = "product_ext_activity"
    __table_args__ = {"comment": "活动扩展表"}

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), unique=True, nullable=False, comment="商品ID"
    )
    booking_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BookingUnit.PERSON.value,
        server_default=BookingUnit.PERSON.value,
        comment="预约单位: person/group"
    )
    time_slots: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]",
        comment="场次 [{start,end,capacity}]"
    )
    event_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="特定活动日期"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="ext_activity")


class ProductExtShop(Base):
    """商品售卖扩展表"""

    __tablename__ = "product_ext_shop"
    __table_args__ = {"comment": "商品售卖扩展表"}

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), unique=True, nullable=False, comment="商品ID"
    )
    has_sku: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="多规格"
    )
    spec_definitions: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment='规格定义 [{name:"颜色",values:["红","蓝"]}]'
    )
    shipping_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="需邮寄"
    )
    shop_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ShopType.ONSITE.value,
        server_default=ShopType.ONSITE.value,
        comment="类型: onsite(小商店)/online(周边)"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="ext_shop")


class SKU(Base):
    """SKU（库存最小单位）表"""

    __tablename__ = "sku"
    __table_args__ = (
        Index("idx_sku_product", "product_id"),
        {"comment": "SKU表"},
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=False, comment="所属商品"
    )
    sku_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="SKU编码"
    )
    spec_values: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}",
        comment='规格值 {color:"红",size:"M"}'
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="SKU价格"
    )
    stock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="当前库存"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SKUStatus.ACTIVE.value,
        server_default=SKUStatus.ACTIVE.value,
        comment="状态: active/inactive"
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="SKU图片"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="skus")
    cart_items: Mapped[List["CartItem"]] = relationship(
        back_populates="sku", lazy="noload"
    )
    inventories: Mapped[List["Inventory"]] = relationship(
        back_populates="sku", lazy="noload"
    )


class PricingRule(Base):
    """定价规则表"""

    __tablename__ = "pricing_rule"
    __table_args__ = (
        Index("idx_pricing_product", "product_id"),
        {"comment": "定价规则表"},
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=False, comment="商品ID"
    )
    rule_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="规则类型: date_type/custom_date"
    )
    date_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="日期类型: weekday/weekend/holiday"
    )
    custom_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="特定日期"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="价格"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="pricing_rules")


class DateTypeConfig(Base):
    """日期类型配置表"""

    __tablename__ = "date_type_config"
    __table_args__ = (
        UniqueConstraint("date", "site_id", name="idx_dtc_date_site"),
        {"comment": "日期类型配置表"},
    )

    date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="日期"
    )
    date_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="日期类型: weekday/weekend/holiday/custom"
    )
    label: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment='标签(如"国庆节")'
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )


class DiscountRule(Base):
    """优惠规则表"""

    __tablename__ = "discount_rule"
    __table_args__ = (
        Index("idx_discount_product", "product_id"),
        Index("idx_discount_site", "site_id"),
        {"comment": "优惠规则表"},
    )

    product_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=True, comment="商品ID, NULL=全局"
    )
    rule_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="规则类型: consecutive_days/multi_person/member_discount"
    )
    threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="阈值"
    )
    discount_rate: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False,
        comment="折扣率(0.80=8折)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        server_default="active", comment="状态"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    product: Mapped[Optional["Product"]] = relationship(
        back_populates="discount_rules"
    )


class Inventory(Base):
    """库存表"""

    __tablename__ = "inventory"
    __table_args__ = (
        Index("idx_inv_product_date", "product_id", "date"),
        Index("idx_inv_sku", "sku_id"),
        Index("idx_inv_site_date", "site_id", "date"),
        {"comment": "库存表"},
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=False, comment="商品ID"
    )
    sku_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sku.id"), nullable=True, comment="SKU ID"
    )
    date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="日期"
    )
    time_slot: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="场次(14:00-15:00)"
    )
    total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="总库存"
    )
    available: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="可用"
    )
    locked: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="锁定中"
    )
    sold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="已售"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InventoryStatus.OPEN.value,
        server_default=InventoryStatus.OPEN.value,
        comment="状态: open/closed"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    product: Mapped["Product"] = relationship(back_populates="inventories")
    sku: Mapped[Optional["SKU"]] = relationship(back_populates="inventories")
    logs: Mapped[List["InventoryLog"]] = relationship(
        back_populates="inventory", lazy="noload"
    )


class InventoryLog(Base):
    """库存变动日志"""

    __tablename__ = "inventory_log"
    __table_args__ = (
        Index("idx_inv_log_inventory", "inventory_id"),
        Index("idx_inv_log_order", "order_id"),
        {"comment": "库存变动日志"},
    )

    inventory_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inventory.id"), nullable=False, comment="库存ID"
    )
    change_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="变动类型: lock/unlock/sell/refund/restock/manual_adjust"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="变动量(正增负减)"
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="关联订单"
    )
    operator_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="操作人"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="备注"
    )

    # 关系
    inventory: Mapped["Inventory"] = relationship(back_populates="logs")
