"""
订单相关模型
- Order（订单表）
- OrderItem（订单项表）
- Cart（购物车表）
- CartItem（购物车项表）
- Ticket（电子票表）
- TicketVerifyLog（核销日志表）
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
import sqlalchemy as sa
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
    TEMPORARY = "temporary"


class RefundStatus(str, enum.Enum):
    NONE = "none"
    PENDING = "pending"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    REJECTED = "rejected"


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


class VerifyResult(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DUPLICATE = "duplicate"


# ---- 模型 ----

class Order(Base):
    """订单表"""

    __tablename__ = "order"
    __table_args__ = (
        Index("idx_order_user_status", "user_id", "status"),
        Index(
            "uq_order_annual_pending_active",
            "user_id",
            "site_id",
            unique=True,
            postgresql_where=sa.text(
                "order_type = 'annual_card' "
                "AND status = 'pending_payment' "
                "AND payment_status = 'unpaid' "
                "AND is_deleted = false"
            ),
        ),
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
    biz_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="业务扩展数据，会员卡/临时单等非商品订单使用"
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
    source_qrcode_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="来源小程序码ID"
    )
    source_channel: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="来源渠道"
    )
    source_scanned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="来源扫码时间"
    )
    refunded_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0",
        comment="累计已退款金额"
    )
    settled_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0",
        comment="累计已结算金额"
    )
    settlement_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unsettled", server_default="unsettled",
        comment="结算状态: unsettled/partial/settled/failed"
    )
    refund_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none", server_default="none",
        comment="退款状态: none/pending/partial/refunded/rejected"
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

    @property
    def user_nickname(self) -> Optional[str]:
        user = self.__dict__.get("user")
        return getattr(user, "nickname", None) if user else None

    @property
    def user_phone(self) -> Optional[str]:
        user = self.__dict__.get("user")
        return getattr(user, "phone", None) if user else None

    @property
    def user_phone_masked(self) -> Optional[str]:
        phone = self.user_phone
        if phone and len(phone) >= 11:
            return f"{phone[:3]}****{phone[-4:]}"
        return phone


class TemporaryOrderSession(Base):
    """现场临时订单/收款会话。

    会话先记录现场商品或自定义金额，用户扫码认领后再转正式订单；
    付款码场景也通过该会话记录操作人、金额与支付审计。
    """

    __tablename__ = "temporary_order_session"
    __table_args__ = (
        Index("idx_temp_order_session_site_status", "site_id", "status"),
        Index("idx_temp_order_session_token", "site_id", "token_hash"),
        Index("idx_temp_order_session_order", "order_id"),
        Index("uq_temp_order_session_no", "session_no", unique=True),
        {"comment": "现场临时订单/收款会话"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    session_no: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, comment="临时会话号"
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="扫码认领 Token 摘要"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", server_default="draft",
        comment="状态: draft/pending_payment/paid/expired/cancelled/refunded"
    )
    payment_flow: Mapped[str] = mapped_column(
        String(30), nullable=False, default="customer_scan_qr", server_default="customer_scan_qr",
        comment="收款方式: customer_scan_qr/merchant_scan_code"
    )
    mode: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="临时单模式: product/custom_amount"
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="商品ID"
    )
    sku_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="SKU ID"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", comment="数量"
    )
    booking_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="预约日期"
    )
    time_slot: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="场次"
    )
    item_name: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True, comment="自定义收款项名称"
    )
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="自定义收款金额"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="现场收款备注"
    )
    created_by_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="创建人ID"
    )
    created_by_source: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="创建来源: admin/user"
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("order.id"), nullable=True, comment="转化后的正式订单ID"
    )
    expire_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="会话过期时间"
    )
    audit_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="现场收款审计数据"
    )


class OrderItem(Base):
    """订单项表（多日票按天拆分）"""

    __tablename__ = "order_item"
    __table_args__ = (
        Index("idx_order_item_order", "order_id"),
        Index("idx_order_item_product", "product_id"),
        Index("idx_order_item_inventory_pool", "inventory_pool_id"),
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
    inventory_pool_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("inventory_pool.id"), nullable=True,
        comment="v1.8 订单锁定的共享库存池ID"
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
        comment="退款状态: none/pending/partial/refunded"
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
        Index("idx_ticket_site", "site_id"),
        Index("idx_ticket_order", "order_id"),
        Index("idx_ticket_user", "user_id"),
        Index("idx_ticket_verify_date", "verify_date"),
        Index("idx_ticket_qr_token_hash", "qr_token_hash"),
        {"comment": "电子票表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
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
    qr_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="二维码Token摘要(仅保存SHA256)"
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


class TicketVerifyLog(Base):
    """票券核销日志表"""

    __tablename__ = "ticket_verify_log"
    __table_args__ = (
        Index("idx_ticket_verify_log_ticket", "ticket_id"),
        Index("idx_ticket_verify_log_staff", "staff_id"),
        Index("idx_ticket_verify_log_staff_source", "site_id", "staff_source", "staff_id", "created_at"),
        Index("idx_ticket_verify_log_site_created", "site_id", "created_at"),
        {"comment": "票券核销日志表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    ticket_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("ticket.id"), nullable=True, comment="票券ID"
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("order.id"), nullable=True, comment="订单ID"
    )
    order_item_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("order_item.id"), nullable=True, comment="订单项ID"
    )
    staff_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="核销员工ID"
    )
    staff_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", server_default="user",
        comment="核销员工来源: user/admin"
    )
    verify_result: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="核销结果: success/failed/duplicate"
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="失败原因"
    )
    device_info: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="设备信息"
    )
    qr_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="二维码 token 摘要"
    )
