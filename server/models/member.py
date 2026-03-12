"""
会员相关模型
- AnnualCardConfig（年卡配置表）
- AnnualCard（年卡实例表）
- AnnualCardBookingRecord（年卡预定记录表）
- TimesCardConfig（次数卡配置表）
- TimesCard（次数卡实例表）
- ActivationCode（激活码表）
- TimesConsumptionRule（次数消耗规则表）
- PointsRecord（积分记录表）
- PointsExchangeConfig（积分兑换配置表）
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User


# ---- 枚举类型 ----

class AnnualCardStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class TimesCardStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"


class ActivationCodeStatus(str, enum.Enum):
    UNUSED = "unused"
    USED = "used"
    EXPIRED = "expired"


class BookingRecordStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class PointsChangeType(str, enum.Enum):
    EARN = "earn"
    CONSUME = "consume"
    REFUND_DEDUCT = "refund_deduct"
    EXPIRE = "expire"
    MANUAL_ADJUST = "manual_adjust"


class ExchangeType(str, enum.Enum):
    FREE_BOOKING = "free_booking"
    DISCOUNT = "discount"
    PRODUCT = "product"


# ---- 模型 ----

class AnnualCardConfig(Base):
    """年卡配置表"""

    __tablename__ = "annual_card_config"
    __table_args__ = (
        Index("idx_acc_site", "site_id"),
        {"comment": "年卡配置表"},
    )

    card_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="卡名称"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="价格"
    )
    duration_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=365, server_default="365",
        comment="有效天数"
    )
    privileges: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="'{}'",
        comment="权益 {product_id: {free:true, limit:0/N}}"
    )
    daily_limit_position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
        comment="按位置每日限额"
    )
    daily_limit_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2, server_default="2",
        comment="按人数每日限额"
    )
    max_consecutive_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5",
        comment="最大连续天数"
    )
    gap_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2, server_default="2",
        comment="中断天数"
    )
    refund_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7, server_default="7",
        comment="退款期"
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
    annual_cards: Mapped[List["AnnualCard"]] = relationship(
        back_populates="config", lazy="noload"
    )


class AnnualCard(Base):
    """年卡实例表"""

    __tablename__ = "annual_card"
    __table_args__ = (
        Index("idx_ac_user", "user_id"),
        Index("idx_ac_config", "config_id"),
        Index("idx_ac_site_status", "site_id", "status"),
        {"comment": "年卡实例表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    config_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="配置ID"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="购买订单ID"
    )
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="开始日期"
    )
    end_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="结束日期"
    )
    # 身份证号（AES-256加密存储），实际加解密在Service层处理
    id_card_encrypted: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="身份证号(AES-256加密)"
    )
    id_card_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="身份证号哈希"
    )
    real_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="实名"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=AnnualCardStatus.ACTIVE.value,
        server_default=AnnualCardStatus.ACTIVE.value,
        comment="状态: active/expired/refunded"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="annual_cards")
    config: Mapped["AnnualCardConfig"] = relationship(
        back_populates="annual_cards"
    )
    booking_records: Mapped[List["AnnualCardBookingRecord"]] = relationship(
        back_populates="annual_card", lazy="noload"
    )


class AnnualCardBookingRecord(Base):
    """年卡预定记录表（滑动窗口辅助）"""

    __tablename__ = "annual_card_booking_record"
    __table_args__ = (
        Index("idx_acbr_card_date", "annual_card_id", "booking_date"),
        Index("idx_acbr_card_status", "annual_card_id", "status"),
        {"comment": "年卡预定记录表"},
    )

    annual_card_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="年卡ID"
    )
    booking_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="预定日期"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单ID"
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="商品ID"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=BookingRecordStatus.ACTIVE.value,
        server_default=BookingRecordStatus.ACTIVE.value,
        comment="状态: active/cancelled"
    )

    # 关系
    annual_card: Mapped["AnnualCard"] = relationship(
        back_populates="booking_records"
    )


class TimesCardConfig(Base):
    """次数卡配置表"""

    __tablename__ = "times_card_config"
    __table_args__ = (
        Index("idx_tcc_site", "site_id"),
        {"comment": "次数卡配置表"},
    )

    card_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="卡名称"
    )
    total_times: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="总次数"
    )
    validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="有效天数(从激活日算)"
    )
    applicable_products: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'",
        comment="适用商品白名单 [product_id,...]"
    )
    daily_limit: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None,
        comment="每日限额(NULL=无限)"
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
    times_cards: Mapped[List["TimesCard"]] = relationship(
        back_populates="config", lazy="noload"
    )
    activation_codes: Mapped[List["ActivationCode"]] = relationship(
        back_populates="config", lazy="noload"
    )
    consumption_rules: Mapped[List["TimesConsumptionRule"]] = relationship(
        back_populates="config", lazy="noload"
    )


class TimesCard(Base):
    """次数卡实例表"""

    __tablename__ = "times_card"
    __table_args__ = (
        Index("idx_tc_user", "user_id"),
        Index("idx_tc_config", "config_id"),
        Index("idx_tc_site_status", "site_id", "status"),
        {"comment": "次数卡实例表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    config_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="配置ID"
    )
    activation_code_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="激活码ID"
    )
    total_times: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="总次数"
    )
    remaining_times: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="剩余次数"
    )
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="= DATE(activated_at)"
    )
    end_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="= start_date + validity_days - 1"
    )
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="激活时间"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=TimesCardStatus.ACTIVE.value,
        server_default=TimesCardStatus.ACTIVE.value,
        comment="状态: active/expired/exhausted"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="times_cards")
    config: Mapped["TimesCardConfig"] = relationship(
        back_populates="times_cards"
    )


class ActivationCode(Base):
    """激活码表"""

    __tablename__ = "activation_code"
    __table_args__ = (
        Index("idx_ac_code_config", "config_id"),
        Index("idx_ac_code_batch", "batch_no"),
        Index("idx_ac_code_site", "site_id"),
        {"comment": "激活码表"},
    )

    code: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False, comment="16位字母数字激活码"
    )
    config_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="次数卡配置ID"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=ActivationCodeStatus.UNUSED.value,
        server_default=ActivationCodeStatus.UNUSED.value,
        comment="状态: unused/used/expired"
    )
    used_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="使用者用户ID"
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="使用时间"
    )
    batch_no: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="批次号"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="过期时间"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    config: Mapped["TimesCardConfig"] = relationship(
        back_populates="activation_codes"
    )


class TimesConsumptionRule(Base):
    """次数消耗规则表"""

    __tablename__ = "times_consumption_rule"
    __table_args__ = (
        Index("idx_tcr_config", "config_id"),
        Index("idx_tcr_product", "product_id"),
        {"comment": "次数消耗规则表"},
    )

    config_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="次数卡配置ID"
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="商品ID(须在白名单内)"
    )
    consume_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
        comment="每次消耗次数"
    )

    # 关系
    config: Mapped["TimesCardConfig"] = relationship(
        back_populates="consumption_rules"
    )


class PointsRecord(Base):
    """积分记录表"""

    __tablename__ = "points_record"
    __table_args__ = (
        Index("idx_pr_user", "user_id"),
        Index("idx_pr_type", "change_type"),
        Index("idx_pr_expires", "expires_at"),
        {"comment": "积分记录表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    change_amount: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="变动量(正增负减)"
    )
    balance_after: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="变动后余额"
    )
    change_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="变动类型: earn/consume/refund_deduct/expire/manual_adjust"
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="原因"
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="关联订单ID"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="积分过期时间(获取+12月)"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="points_records")


class PointsExchangeConfig(Base):
    """积分兑换配置表"""

    __tablename__ = "points_exchange_config"
    __table_args__ = (
        Index("idx_pec_site", "site_id"),
        {"comment": "积分兑换配置表"},
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="活动名称"
    )
    exchange_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="兑换类型: free_booking/discount/product"
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="关联商品ID"
    )
    points_required: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="所需积分"
    )
    stock: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="库存"
    )
    stock_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="已兑换数量"
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="开始时间"
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="结束时间"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        server_default="active", comment="状态"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
