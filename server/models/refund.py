"""
退款相关模型
- RefundRecord：退款主记录
- RefundRecordItem：退款订单项明细
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class RefundRecord(Base):
    """退款主记录"""

    __tablename__ = "refund_record"
    __table_args__ = (
        Index("idx_refund_site_status", "site_id", "status"),
        Index("idx_refund_order", "order_id"),
        Index("idx_refund_no", "refund_no", unique=True),
        Index(
            "uq_refund_record_active_order",
            "order_id",
            unique=True,
            postgresql_where=sa.text("status IN ('pending', 'processing') AND is_deleted = false"),
        ),
        {"comment": "退款主记录"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单ID"
    )
    refund_no: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True, comment="退款单号"
    )
    refund_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="退款模式: full/partial/item"
    )
    order_action: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="订单处理: keep_order/cancel_order"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="实际退款金额"
    )
    system_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="系统计算金额"
    )
    release_inventory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
        comment="是否释放库存"
    )
    inventory_released: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="库存是否已实际释放，保障退款回补幂等"
    )
    reason: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="退款原因"
    )
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal", server_default="normal",
        comment="风险等级: normal/medium/high"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending",
        comment="状态: pending/approved/processing/completed/rejected/failed"
    )
    wechat_refund_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="微信退款ID"
    )
    requested_by: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="申请人"
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="审批人"
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审批时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    items: Mapped[list["RefundRecordItem"]] = relationship(
        back_populates="refund_record", lazy="selectin"
    )


class RefundRecordItem(Base):
    """退款订单项明细"""

    __tablename__ = "refund_record_item"
    __table_args__ = (
        Index("idx_refund_item_record", "refund_record_id"),
        Index("idx_refund_item_order_item", "order_item_id"),
        {"comment": "退款订单项明细"},
    )

    refund_record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("refund_record.id"), nullable=False,
        comment="退款记录ID"
    )
    order_item_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单项ID"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="退款金额"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", comment="数量"
    )
    release_inventory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
        comment="是否释放库存"
    )

    refund_record: Mapped[RefundRecord] = relationship(
        back_populates="items", lazy="noload"
    )
