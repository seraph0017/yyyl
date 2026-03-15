"""
财务相关模型
- FinanceAccount（资金账户表）
- FinanceTransaction（交易流水表）
- DepositRecord（押金记录表）
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---- 枚举类型 ----

class TransactionType(str, enum.Enum):
    INCOME = "income"
    REFUND = "refund"
    DEPOSIT_IN = "deposit_in"
    DEPOSIT_OUT = "deposit_out"
    DEPOSIT_DEDUCT = "deposit_deduct"
    WITHDRAW = "withdraw"


class AccountType(str, enum.Enum):
    PENDING = "pending"
    AVAILABLE = "available"
    DEPOSIT = "deposit"
    MAINTENANCE = "maintenance"


class DepositStatus(str, enum.Enum):
    HELD = "held"
    RETURNED = "returned"
    DEDUCTED = "deducted"
    PARTIAL_RETURNED = "partial_returned"


class DamageLevel(str, enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    TOTAL_LOSS = "total_loss"


# ---- 模型 ----

class FinanceAccount(Base):
    """资金账户表"""

    __tablename__ = "finance_account"
    __table_args__ = {"comment": "资金账户表"}

    pending_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0", comment="待确认金额"
    )
    available_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0", comment="可提现金额"
    )
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0", comment="押金专户"
    )
    maintenance_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0", comment="设备维护收入"
    )
    total_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0", comment="累计总收入"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, default=1,
        server_default="1", comment="营地ID"
    )

    # 关系
    transactions: Mapped[list["FinanceTransaction"]] = relationship(
        back_populates="account", lazy="noload",
        primaryjoin="FinanceAccount.site_id == foreign(FinanceTransaction.site_id)",
    )


class FinanceTransaction(Base):
    """交易流水表"""

    __tablename__ = "finance_transaction"
    __table_args__ = (
        Index("idx_ft_order", "order_id"),
        Index("idx_ft_site", "site_id"),
        Index("idx_ft_type", "type"),
        {"comment": "交易流水表"},
    )

    transaction_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, comment="交易流水号"
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="关联订单ID"
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="类型: income/refund/deposit_in/deposit_out/deposit_deduct/withdraw"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="金额"
    )
    account_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="账户类型: pending/available/deposit/maintenance"
    )
    from_account: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="转出方"
    )
    to_account: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="转入方"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed",
        server_default="completed", comment="状态"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="备注"
    )
    operator_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="操作人"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
    # v1.5 退款增强字段
    inventory_released: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
        comment="退款时是否释放了库存"
    )
    custom_amount: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="是否为管理员自定义金额"
    )
    system_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="系统计算的默认退款金额(供审计对比)"
    )
    amount_deviation_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="自定义金额与系统金额的偏差率(%)"
    )

    # 关系
    account: Mapped[Optional["FinanceAccount"]] = relationship(
        back_populates="transactions",
        primaryjoin="foreign(FinanceTransaction.site_id) == FinanceAccount.site_id",
        viewonly=True,
    )


class DepositRecord(Base):
    """押金记录表"""

    __tablename__ = "deposit_record"
    __table_args__ = (
        Index("idx_dr_order", "order_id"),
        Index("idx_dr_status", "status"),
        {"comment": "押金记录表"},
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单ID"
    )
    order_item_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单项ID"
    )
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="押金金额"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=DepositStatus.HELD.value,
        server_default=DepositStatus.HELD.value,
        comment="状态: held/returned/deducted/partial_returned"
    )
    return_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="退还金额"
    )
    deduct_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="扣除金额"
    )
    damage_level: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="损坏等级: minor/moderate/severe/total_loss"
    )
    damage_photos: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="损坏照片URL列表"
    )
    damage_remark: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="损坏备注"
    )
    processed_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="处理人"
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="处理时间"
    )
