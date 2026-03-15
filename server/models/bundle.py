"""
搭配售卖相关模型
- BundleConfig（搭配组合配置表）
- BundleItem（搭配商品项表）
- ProductExtInsurance（保险产品扩展表）
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.product import Product, SKU


# ---- 枚举类型 ----

class BundleStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


# ---- 模型 ----

class BundleConfig(Base):
    """搭配组合配置表"""

    __tablename__ = "bundle_config"
    __table_args__ = (
        Index("idx_bc_main_product", "main_product_id"),
        Index("idx_bc_site_status", "site_id", "status"),
        {"comment": "搭配组合配置表"},
    )

    main_product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=False,
        comment="主商品ID",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="组合名称",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=BundleStatus.ACTIVE.value,
        server_default=BundleStatus.ACTIVE.value,
        comment="状态: active/inactive",
    )
    start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="生效起始时间(NULL=立即生效)",
    )
    end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="生效结束时间(NULL=永不过期)",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )

    # 关系
    main_product: Mapped["Product"] = relationship(
        foreign_keys=[main_product_id], lazy="selectin",
    )
    items: Mapped[List["BundleItem"]] = relationship(
        back_populates="bundle_config", lazy="selectin",
        cascade="all, delete-orphan",
    )


class BundleItem(Base):
    """搭配商品项表"""

    __tablename__ = "bundle_item"
    __table_args__ = (
        Index("idx_bi_config", "bundle_config_id"),
        Index("idx_bi_product", "product_id"),
        {"comment": "搭配商品项表"},
    )

    bundle_config_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bundle_config.id"), nullable=False,
        comment="搭配组合配置ID",
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=False,
        comment="搭配商品ID",
    )
    sku_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sku.id"), nullable=True,
        comment="SKU ID(可选)",
    )
    bundle_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="搭配优惠价(NULL则使用商品原价)",
    )
    max_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
        comment="最大可选数量",
    )
    is_default_checked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="是否默认勾选",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )

    # 关系
    bundle_config: Mapped["BundleConfig"] = relationship(
        back_populates="items",
    )
    product: Mapped["Product"] = relationship(
        foreign_keys=[product_id], lazy="selectin",
    )
    sku: Mapped[Optional["SKU"]] = relationship(
        foreign_keys=[sku_id], lazy="selectin",
    )


class ProductExtInsurance(Base):
    """保险产品扩展表"""

    __tablename__ = "product_ext_insurance"
    __table_args__ = (
        Index("idx_pei_product", "product_id", unique=True),
        {"comment": "保险产品扩展表"},
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product.id"), unique=True, nullable=False,
        comment="商品ID",
    )
    insurer: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="承保机构",
    )
    coverage_content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="保障内容(富文本)",
    )
    coverage_days: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="保障天数",
    )
    claim_phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="理赔电话",
    )
    terms_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="保险条款链接",
    )
    age_min: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="最小投保年龄",
    )
    age_max: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="最大投保年龄",
    )
    claim_process: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="理赔流程说明",
    )
    license_no: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="保险许可证号",
    )

    # 关系
    product: Mapped["Product"] = relationship(
        foreign_keys=[product_id], lazy="selectin",
    )
