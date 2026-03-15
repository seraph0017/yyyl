"""
报销系统相关模型
- ExpenseType（报销类型配置表）
- ExpenseRequest（报销申请表）
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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
    from models.admin import AdminUser


# ---- 枚举类型 ----

class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


# ---- 模型 ----

class ExpenseType(Base):
    """报销类型配置表"""

    __tablename__ = "expense_type"
    __table_args__ = (
        Index("idx_et_site", "site_id"),
        {"comment": "报销类型配置表"},
    )

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="类型名称",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="类型描述",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        server_default="active", comment="状态: active/inactive",
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
    requests: Mapped[list["ExpenseRequest"]] = relationship(
        back_populates="expense_type", lazy="noload",
    )


class ExpenseRequest(Base):
    """报销申请表"""

    __tablename__ = "expense_request"
    __table_args__ = (
        Index("idx_er_user", "user_id"),
        Index("idx_er_status", "status"),
        Index("idx_er_site", "site_id"),
        Index("idx_er_type_date", "expense_type_id", "created_at"),
        CheckConstraint(
            "reviewer_id IS NULL OR reviewer_id != user_id",
            name="ck_er_no_self_review",
        ),
        {"comment": "报销申请表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=False,
        comment="报销人(管理员ID)",
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=True,
        comment="代提交人(NULL=本人)",
    )
    expense_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expense_type.id"), nullable=False,
        comment="报销类型ID",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="报销金额",
    )
    expense_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="费用发生日期",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="报销说明",
    )
    receipt_images: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]",
        comment="凭证图片URL列表",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=ExpenseStatus.PENDING.value,
        server_default=ExpenseStatus.PENDING.value,
        comment="状态: pending/approved/rejected/paid",
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=True,
        comment="审批人(约束: != user_id)",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审批时间",
    )
    review_remark: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="审批备注",
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="打款时间",
    )
    paid_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=True,
        comment="打款操作人",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )

    # 关系
    expense_type: Mapped["ExpenseType"] = relationship(
        back_populates="requests",
    )
    applicant: Mapped["AdminUser"] = relationship(
        foreign_keys=[user_id], lazy="selectin",
    )
    reviewer: Mapped[Optional["AdminUser"]] = relationship(
        foreign_keys=[reviewer_id], lazy="selectin",
    )
