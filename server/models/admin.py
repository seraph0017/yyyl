"""
管理员相关模型
- AdminUser（管理员表）
- AdminRole（角色表）
- AdminPermission（权限表）
- OperationLog（操作日志表）
- DailyReport（日报表）
- WeeklyReport（周报表）
- MonthlyReport（月报表）
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---- 枚举类型 ----

class AdminStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class RoleCode(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    STAFF = "staff"


class PermissionResource(str, enum.Enum):
    PRODUCT = "product"
    ORDER = "order"
    MEMBER = "member"
    FINANCE = "finance"
    INVENTORY = "inventory"
    TICKET = "ticket"
    DASHBOARD = "dashboard"
    SYSTEM = "system"
    FAQ = "faq"
    NOTIFICATION = "notification"
    TIMES_CARD = "times_card"
    PAGE_CONFIG = "page_config"
    OPERATION_LOG = "operation_log"


class PermissionAction(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"


class ConfirmResult(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    LOCKED = "locked"


# ---- 模型 ----

class AdminUser(Base):
    """管理员表"""

    __tablename__ = "admin_user"
    __table_args__ = (
        Index("idx_admin_site", "site_id"),
        {"comment": "管理员表"},
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, unique=True, nullable=True, comment="关联用户ID"
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, nullable=True, comment="用户名"
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="密码哈希"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    real_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="真实姓名"
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("admin_role.id"), nullable=True, comment="角色ID"
    )
    operation_password_hash: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="操作密码哈希"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=AdminStatus.ACTIVE.value,
        server_default=AdminStatus.ACTIVE.value,
        comment="状态: active/disabled"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后登录时间"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    role: Mapped[Optional["AdminRole"]] = relationship(
        back_populates="admin_users", lazy="selectin"
    )


class AdminRole(Base):
    """角色表"""

    __tablename__ = "admin_role"
    __table_args__ = (
        Index("idx_ar_site", "site_id"),
        {"comment": "管理员角色表"},
    )

    role_name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="角色名称"
    )
    role_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False,
        comment="角色代码: super_admin/admin/staff"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="描述"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    admin_users: Mapped[List["AdminUser"]] = relationship(
        back_populates="role", lazy="noload"
    )
    permissions: Mapped[List["AdminPermission"]] = relationship(
        back_populates="role", lazy="selectin"
    )


class AdminPermission(Base):
    """权限表"""

    __tablename__ = "admin_permission"
    __table_args__ = (
        Index("idx_ap_role", "role_id"),
        {"comment": "管理员权限表"},
    )

    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_role.id"), nullable=False, comment="角色ID"
    )
    resource: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="资源: product/order/member/finance/inventory/ticket/dashboard/system/faq/notification/times_card/page_config/operation_log"
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="操作: read/write/delete/export"
    )

    # 关系
    role: Mapped["AdminRole"] = relationship(back_populates="permissions")


class OperationLog(Base):
    """操作日志表"""

    __tablename__ = "operation_log"
    __table_args__ = (
        Index("idx_ol_operator", "operator_id"),
        Index("idx_ol_target", "target_type", "target_id"),
        Index("idx_ol_site", "site_id"),
        Index("idx_ol_high_risk", "is_high_risk"),
        {"comment": "操作日志表"},
    )

    operator_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="操作人ID"
    )
    operator_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="操作人姓名"
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="操作"
    )
    target_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="目标类型"
    )
    target_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="目标ID"
    )
    detail: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="变更前后值"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True, comment="IP地址"
    )
    is_high_risk: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="高风险操作"
    )
    confirm_result: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="确认结果: passed/failed/locked"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )


class DailyReport(Base):
    """日报表"""

    __tablename__ = "daily_report"
    __table_args__ = (
        UniqueConstraint("report_date", "site_id", name="uq_daily_report_date_site"),
        {"comment": "日报表"},
    )

    report_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="报表日期"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="当日总订单数"
    )
    paid_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="已支付订单数"
    )
    cancelled_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="取消订单数"
    )
    refunded_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="退款订单数"
    )
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="总收入（元）"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="退款金额（元）"
    )
    net_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="净收入"
    )
    new_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="新增用户数"
    )
    active_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="活跃用户数"
    )
    new_members: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="新增年卡会员数"
    )
    camping_occupancy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="营位入住率(%)"
    )
    avg_order_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="平均客单价"
    )
    category_breakdown: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="各品类收入明细 [{category, orders, revenue}]"
    )
    payment_channel_stats: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="支付渠道统计 [{channel, count, amount}]"
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="报表生成时间"
    )


class WeeklyReport(Base):
    """周报表"""

    __tablename__ = "weekly_report"
    __table_args__ = (
        UniqueConstraint("week_start", "site_id", name="uq_weekly_report_start_site"),
        {"comment": "周报表"},
    )

    week_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="周起始日期(周一)"
    )
    week_end: Mapped[date] = mapped_column(
        Date, nullable=False, comment="周结束日期(周日)"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="周总订单数"
    )
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="周总收入"
    )
    net_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="周净收入"
    )
    new_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="周新增用户数"
    )
    active_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="周活跃用户数"
    )
    avg_occupancy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="周平均入住率(%)"
    )
    top_products: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="TOP10热销商品 [{product_id, name, orders, revenue}]"
    )
    daily_trends: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="每日趋势数据 [{date, orders, revenue}]"
    )
    wow_order_growth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="订单周环比增长率(%)"
    )
    wow_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="收入周环比增长率(%)"
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="报表生成时间"
    )


class MonthlyReport(Base):
    """月报表"""

    __tablename__ = "monthly_report"
    __table_args__ = (
        UniqueConstraint(
            "report_year", "report_month", "site_id",
            name="uq_monthly_report_ym_site",
        ),
        {"comment": "月报表"},
    )

    report_year: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="报表年份"
    )
    report_month: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="报表月份(1-12)"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="月总订单数"
    )
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="月总收入"
    )
    net_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="月净收入"
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0,
        server_default="0.00", comment="月退款总额"
    )
    new_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="月新增用户数"
    )
    active_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="月活跃用户数"
    )
    total_members: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="月末累计会员数"
    )
    avg_occupancy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="月平均入住率(%)"
    )
    category_breakdown: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="各品类月度收入明细"
    )
    weekly_trends: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="每周趋势数据 [{week, orders, revenue}]"
    )
    mom_order_growth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="订单月环比增长率(%)"
    )
    mom_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="收入月环比增长率(%)"
    )
    yoy_order_growth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="订单同比增长率(%)"
    )
    yoy_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="收入同比增长率(%)"
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="报表生成时间"
    )
