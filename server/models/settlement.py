"""
资金结算模型
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class FinanceSettlement(Base):
    """订单资金结算记录"""

    __tablename__ = "finance_settlement"
    __table_args__ = (
        UniqueConstraint("order_id", "settlement_no", name="uq_settlement_order_no"),
        Index("idx_settlement_site_status", "site_id", "status"),
        Index("idx_settlement_order", "order_id"),
        {"comment": "订单资金结算记录"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单ID"
    )
    settlement_no: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="结算单号"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="结算金额"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed", server_default="completed",
        comment="状态: completed/failed"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="触发方式"
    )
    settled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="结算时间"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="失败原因"
    )
