"""
订单相关模型
- Order（订单表）
- OrderItem（订单项表）
- Cart（购物车表）
- CartItem（购物车项表）
- Ticket（电子票表）
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.product import Product, SKU
    from models.user import User, UserIdentity


# ---- 枚举类型 ----

class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    VERIFIED = "verified"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"


class PaymentMethod(str, enum.Enum):
    WECHAT_PAY = "wechat_pay"
    MOCK_PAY = "mock_pay"
    ANNUAL_CARD_FREE = "annual_card_free"
    TIMES_CARD = "times_card"
    POINTS_EXCHANGE = "points_exchange"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"


class OrderType(str, enum.Enum):
    DAILY_CAMPING = "daily_camping"
    EVENT_CAMPING = "event_camping"
    RENTAL = "rental"
    DAILY_ACTIVITY = "daily_activity"
    SPECIAL_ACTIVITY = "special_activity"
    SHOP = "shop"
    MERCHANDISE = "merchandise"
    ANNUAL_CARD = "annual_card"
    BUNDLE_ADDON = "bundle_addon"


class RefundStatus(str, enum.Enum):
    NONE = "none"
    REFUNDED = "refunded"


class DiscountType(str, enum.Enum):
    CONSECUTIVE_DAYS = "consecutive_days"
    MULTI_PERSON = "multi_person"
    MEMBER = "member"
    NONE = "none"


class TicketType(str, enum.Enum):
    CAMPING = "camping"
    RENTAL = "rental"
    ACTIVITY = "activity"


class VerifyStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"


# ---- 模型 ----

class Order(Base):
    """订单表"""

    __tablename__ = "order"
    __table_args__ = (
        Index("idx_order_user_status", "user_id", "status"),
        Index(
            "idx_order_expire", "expire_at",
            postgresql_where="status = 'pending_payment'",
        ),
        Index("idx_order_site", "site_id"),
        {"comment": "订单表"},
    )

    order_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, comment="订单号"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user.id"), nullable=False, comment="用户ID"
    )
    parent_order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("order.id"), nullable=True, comment="父订单ID(购物车拆单)"
    )
    order_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="订单类型: 同Product.type + annual_card"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=OrderStatus.PENDING_PAYMENT.value,
        server_default=OrderStatus.PENDING_PAYMENT.value,
        comment="订单状态"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="总金额"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="优惠金额"
    )
    actual_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="实付金额"
    )
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0,
        server_default="0", comment="押金(租赁)"
    )
    discount_type: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        comment="优惠类型: consecutive_days/multi_person/member/none"
    )
    discount_detail: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="优惠明细"
    )
    payment_method: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=PaymentMethod.MOCK_PAY.value,
        server_default=PaymentMethod.MOCK_PAY.value,
        comment="支付方式"
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=PaymentStatus.UNPAID.value,
        server_default=PaymentStatus.UNPAID.value,
        comment="支付状态"
    )
    payment_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="支付时间"
    )
    payment_no: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="支付流水号"
    )
    times_card_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="使用的次数卡ID"
    )
    times_consumed: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="消耗次数"
    )
    address_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="收货地址(周边商品)"
    )
    shipping_no: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="物流单号"
    )
    shipping_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="物流状态"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="备注"
    )
    expire_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="支付截止时间"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
    refunded_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0",
        comment="累计已退款金额"
    )
    assigned_staff_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True,
        comment="绩效归属员工ID(手动指派)"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", lazy="selectin",
        foreign_keys="OrderItem.order_id",
    )
    children: Mapped[List["Order"]] = relationship(
        back_populates="parent",
        foreign_keys="Order.parent_order_id",
        lazy="noload",
    )
    parent: Mapped[Optional["Order"]] = relationship(
        back_populates="children",
        foreign_keys="Order.parent_order_id",
        remote_side="Order.id",
        lazy="noload",
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="order", lazy="noload"
    )


class OrderItem(Base):
    """订单项表（多日票按天拆分）"""

    __tablename__ = "order_item"
    __table_args__ = (
        Index("idx_order_item_order", "order_id"),
        Index("idx_order_item_product", "product_id"),
        {"comment": "订单项表"},
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("order.id"), nullable=False, comment="订单ID"
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="商品ID"
    )
    sku_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="SKU ID"
    )
    date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="日期(多日票每天一条)"
    )
    time_slot: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="场次"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
        comment="数量"
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="该天原价"
    )
    actual_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="折后实付"
    )
    identity_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="出行人"
    )
    parent_item_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="加人票关联原票"
    )
    refund_status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=RefundStatus.NONE.value,
        server_default=RefundStatus.NONE.value,
        comment="退款状态: none/refunded"
    )
    bundle_group_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True,
        comment="搭配组合实例ID(同一次搭配操作共享, 格式BG{timestamp}{random})"
    )
    bundle_config_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True,
        comment="搭配配置来源ID(FK→bundle_config)"
    )
    is_bundle_item: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="是否为搭配项"
    )

    # 关系
    order: Mapped["Order"] = relationship(
        back_populates="items",
        foreign_keys=[order_id],
    )
    ticket: Mapped[Optional["Ticket"]] = relationship(
        back_populates="order_item", uselist=False, lazy="noload",
    )


class Cart(Base):
    """购物车表"""

    __tablename__ = "cart"
    __table_args__ = {"comment": "购物车表"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user.id"), unique=True, nullable=False, comment="用户ID"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="cart")
    items: Mapped[List["CartItem"]] = relationship(
        back_populates="cart", lazy="selectin"
    )


class CartItem(Base):
    """购物车项表"""

    __tablename__ = "cart_item"
    __table_args__ = (
        Index("idx_cart_item_cart", "cart_id"),
        {"comment": "购物车项表"},
    )

    cart_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cart.id"), nullable=False, comment="购物车ID"
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="商品ID"
    )
    sku_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sku.id"), nullable=True, comment="SKU ID"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
        comment="数量"
    )
    checked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
        comment="选中"
    )

    # 关系
    cart: Mapped["Cart"] = relationship(back_populates="items")
    sku: Mapped[Optional["SKU"]] = relationship(back_populates="cart_items")


class Ticket(Base):
    """电子票表"""

    __tablename__ = "ticket"
    __table_args__ = (
        Index("idx_ticket_order", "order_id"),
        Index("idx_ticket_user", "user_id"),
        Index("idx_ticket_verify_date", "verify_date"),
        {"comment": "电子票表"},
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("order.id"), nullable=False, comment="订单ID"
    )
    order_item_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("order_item.id"), nullable=True, comment="订单项ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user.id"), nullable=False, comment="用户ID"
    )
    ticket_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, comment="票号"
    )
    ticket_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="票类型: camping/rental/activity"
    )
    qr_token: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="二维码Token(30秒刷新)"
    )
    qr_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="二维码Token过期时间"
    )
    verify_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="待验日期"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="验票时间"
    )
    verified_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="验票员"
    )
    verify_status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=VerifyStatus.PENDING.value,
        server_default=VerifyStatus.PENDING.value,
        comment="验票状态: pending/verified/expired"
    )
    total_verify_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="多日票总验次数"
    )
    current_verify_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="已验次数"
    )

    # 关系
    order: Mapped["Order"] = relationship(back_populates="tickets")
    order_item: Mapped[Optional["OrderItem"]] = relationship(
        back_populates="ticket"
    )
