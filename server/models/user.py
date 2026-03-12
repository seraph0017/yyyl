"""
用户相关模型
- User（用户表）
- UserAddress（收货地址表）
- UserIdentity（出行人身份信息表）
- IdentityFieldConfig（身份登记字段配置表）
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.member import AnnualCard, PointsRecord, TimesCard
    from models.notification import Notification
    from models.order import Cart, Order


# ---- 枚举类型 ----

class UserRole(str, enum.Enum):
    USER = "user"
    STAFF = "staff"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class MemberLevel(str, enum.Enum):
    NORMAL = "normal"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


# ---- 模型 ----

class User(Base):
    """用户表"""

    __tablename__ = "user"
    __table_args__ = (
        Index("idx_user_phone", "phone"),
        Index("idx_user_site_role", "site_id", "role"),
        Index("idx_user_member_level", "member_level"),
        {"comment": "用户表"},
    )

    openid: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="微信小程序OpenID"
    )
    unionid: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True, comment="微信UnionID"
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="微信昵称"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="头像URL"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserRole.USER.value,
        server_default=UserRole.USER.value, comment="角色: user/staff/admin"
    )
    is_member: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="是否普通会员"
    )
    points_balance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="积分余额"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="最后登录时间"
    )
    member_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MemberLevel.NORMAL.value,
        server_default=MemberLevel.NORMAL.value,
        comment="会员等级: normal/silver/gold/platinum"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserStatus.ACTIVE.value,
        server_default=UserStatus.ACTIVE.value,
        comment="用户状态: active/disabled/deleted"
    )

    # 关系
    addresses: Mapped[List["UserAddress"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    identities: Mapped[List["UserIdentity"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    orders: Mapped[List["Order"]] = relationship(
        back_populates="user", lazy="noload"
    )
    cart: Mapped[Optional["Cart"]] = relationship(
        back_populates="user", uselist=False, lazy="noload"
    )
    annual_cards: Mapped[List["AnnualCard"]] = relationship(
        back_populates="user", lazy="noload"
    )
    times_cards: Mapped[List["TimesCard"]] = relationship(
        back_populates="user", lazy="noload"
    )
    points_records: Mapped[List["PointsRecord"]] = relationship(
        back_populates="user", lazy="noload"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="user", lazy="noload"
    )


class UserAddress(Base):
    """收货地址表"""

    __tablename__ = "user_address"
    __table_args__ = (
        Index("idx_user_address_user", "user_id"),
        {"comment": "收货地址表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    contact_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="收货人"
    )
    contact_phone: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="手机号"
    )
    province: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="省"
    )
    city: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="市"
    )
    district: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="区"
    )
    detail: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="详细地址"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="默认地址"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="addresses")


class UserIdentity(Base):
    """出行人身份信息表"""

    __tablename__ = "user_identity"
    __table_args__ = (
        Index("idx_user_identity_user", "user_id"),
        Index("idx_user_identity_hash", "id_card_hash"),
        {"comment": "出行人身份信息表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="姓名"
    )
    # 身份证号（AES-256加密存储），实际加解密在Service层处理
    id_card_encrypted: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="身份证号（AES-256加密）"
    )
    id_card_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="身份证号哈希（查询用）"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    custom_fields: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="自定义字段 [{field_id, field_name, value}]"
    )
    is_self: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="是否本人"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="identities")


class IdentityFieldConfig(Base):
    """身份登记字段配置表"""

    __tablename__ = "identity_field_config"
    __table_args__ = (
        Index("idx_ifc_product", "product_id"),
        Index("idx_ifc_site", "site_id"),
        {"comment": "身份登记字段配置表"},
    )

    product_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="商品ID, NULL=全局默认"
    )
    registration_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="required",
        server_default="required",
        comment="登记模式: required/optional/none"
    )
    builtin_fields: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="'{}'",
        comment="内置字段配置 {name:{enabled,required}, id_card:{...}, phone:{...}}"
    )
    custom_fields: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'",
        comment="自定义字段 [{field_name,field_type,required,options,sort_order}]"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
