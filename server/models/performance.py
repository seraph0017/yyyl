"""
绩效统计相关模型
- PerformanceConfig（绩效系数配置表）
- PerformanceRecord（绩效汇总记录表）
- PerformanceDetail（绩效分项明细表——纵表设计）
"""

from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.admin import AdminUser


# ---- 枚举类型 ----

class IncomeType(str, enum.Enum):
    CAMPSITE = "campsite"
    RENTAL = "rental"
    SHOP = "shop"
    ACTIVITY = "activity"
    MEMBERSHIP = "membership"


class PeriodType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ---- 模型 ----

class PerformanceConfig(Base):
    """绩效系数配置表"""

    __tablename__ = "performance_config"
    __table_args__ = (
        UniqueConstraint("income_type", "site_id", name="uq_pc_income_type_site"),
        Index("idx_pc_site", "site_id"),
        {"comment": "绩效系数配置表"},
    )

    income_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="收入类型: campsite/rental/shop/activity/membership",
    )
    coefficient: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False,
        comment="绩效系数(如0.0300=3%)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="说明",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )


class PerformanceRecord(Base):
    """绩效汇总记录表"""

    __tablename__ = "performance_record"
    __table_args__ = (
        Index("idx_pr_staff", "staff_user_id"),
        Index("idx_pr_period", "period_type", "period_start"),
        Index("idx_pr_site", "site_id"),
        {"comment": "绩效汇总记录表"},
    )

    staff_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=False,
        comment="员工管理员ID",
    )
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="周期类型: daily/weekly/monthly",
    )
    period_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="周期开始日期",
    )
    period_end: Mapped[date] = mapped_column(
        Date, nullable=False, comment="周期结束日期",
    )
    total_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0",
        comment="总收入",
    )
    total_performance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0",
        comment="总绩效",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )

    # 关系
    staff: Mapped["AdminUser"] = relationship(
        foreign_keys=[staff_user_id], lazy="selectin",
    )
    details: Mapped[List["PerformanceDetail"]] = relationship(
        back_populates="record", lazy="selectin",
        cascade="all, delete-orphan",
    )


class PerformanceDetail(Base):
    """绩效分项明细表（纵表设计：每个收入类型一行，扩展新类型无需改表）"""

    __tablename__ = "performance_detail"
    __table_args__ = (
        Index("idx_pd_record", "record_id"),
        {"comment": "绩效分项明细表"},
    )

    record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("performance_record.id"), nullable=False,
        comment="绩效汇总记录ID",
    )
    income_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="收入类型: campsite/rental/shop/activity/membership",
    )
    income_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0",
        comment="该类型收入金额",
    )
    performance_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0",
        comment="该类型绩效金额",
    )

    # 关系
    record: Mapped["PerformanceRecord"] = relationship(
        back_populates="details",
    )
