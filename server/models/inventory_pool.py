"""
v1.8 跨商品共享库存池模型

库存池是商品、SKU、活动场次或租赁资产共享库存的事实源。
绑定关系必须显式声明，禁止通过名称、分类等隐式共享库存。
"""

from __future__ import annotations

import enum
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class InventoryPoolStatus(str, enum.Enum):
    """库存池状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class InventoryPoolType(str, enum.Enum):
    """库存池类型"""

    GENERIC = "generic"
    CAMPSITE = "campsite"
    ACTIVITY = "activity"
    RENTAL = "rental"
    BUNDLE = "bundle"


class InventoryPoolBindingStatus(str, enum.Enum):
    """库存池绑定状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class InventoryPool(Base):
    """跨商品共享库存池"""

    __tablename__ = "inventory_pool"
    __table_args__ = (
        UniqueConstraint("site_id", "pool_code", name="uq_inventory_pool_site_code"),
        CheckConstraint("total >= 0", name="ck_inventory_pool_total_non_negative"),
        CheckConstraint("available >= 0", name="ck_inventory_pool_available_non_negative"),
        CheckConstraint("locked >= 0", name="ck_inventory_pool_locked_non_negative"),
        CheckConstraint("sold >= 0", name="ck_inventory_pool_sold_non_negative"),
        CheckConstraint(
            "available + locked + sold = total",
            name="ck_inventory_pool_quantity_sum",
        ),
        Index("idx_inventory_pool_site_status", "site_id", "status"),
        {"comment": "v1.8 跨商品共享库存池"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    pool_code: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="库存池编码，同营地唯一"
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="库存池名称"
    )
    pool_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=InventoryPoolType.GENERIC.value,
        server_default=InventoryPoolType.GENERIC.value,
        comment="库存池类型: generic/campsite/activity/rental/bundle",
    )
    total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="总库存"
    )
    available: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="可用库存"
    )
    locked: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="锁定库存"
    )
    sold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="已售库存"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InventoryPoolStatus.ACTIVE.value,
        server_default=InventoryPoolStatus.ACTIVE.value,
        comment="状态: active/inactive",
    )

    bindings: Mapped[List["InventoryPoolBinding"]] = relationship(
        back_populates="inventory_pool",
        lazy="noload",
    )


class InventoryPoolBinding(Base):
    """库存池显式绑定关系"""

    __tablename__ = "inventory_pool_binding"
    __table_args__ = (
        Index("idx_inventory_pool_binding_pool", "inventory_pool_id"),
        Index("idx_inventory_pool_binding_site_status", "site_id", "status"),
        Index("idx_inventory_pool_binding_product", "product_id"),
        Index("idx_inventory_pool_binding_sku", "sku_id"),
        Index("idx_inventory_pool_binding_activity", "activity_session_id"),
        Index("idx_inventory_pool_binding_rental", "rental_asset_id"),
        CheckConstraint(
            "("
            "(CASE WHEN product_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN sku_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN activity_session_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN rental_asset_id IS NOT NULL THEN 1 ELSE 0 END)"
            ") = 1",
            name="ck_inventory_pool_binding_exactly_one_target",
        ),
        Index(
            "uq_inventory_pool_binding_active_product",
            "site_id", "product_id",
            unique=True,
            postgresql_where=text("product_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        ),
        Index(
            "uq_inventory_pool_binding_active_sku",
            "site_id", "sku_id",
            unique=True,
            postgresql_where=text("sku_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        ),
        Index(
            "uq_inventory_pool_binding_active_activity",
            "site_id", "activity_session_id",
            unique=True,
            postgresql_where=text("activity_session_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        ),
        Index(
            "uq_inventory_pool_binding_active_rental",
            "site_id", "rental_asset_id",
            unique=True,
            postgresql_where=text("rental_asset_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        ),
        {"comment": "v1.8 库存池绑定关系"},
    )

    inventory_pool_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("inventory_pool.id"),
        nullable=False,
        comment="库存池ID",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("product.id"), nullable=True, comment="商品ID"
    )
    sku_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sku.id"), nullable=True, comment="SKU ID"
    )
    activity_session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="活动场次ID，v1.8 后续场次模型接入"
    )
    rental_asset_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="租赁资产ID，v1.8 后续资产模型接入"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100", comment="匹配优先级"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InventoryPoolBindingStatus.ACTIVE.value,
        server_default=InventoryPoolBindingStatus.ACTIVE.value,
        comment="状态: active/inactive",
    )

    inventory_pool: Mapped["InventoryPool"] = relationship(back_populates="bindings")
