"""
内容相关模型
- DisclaimerTemplate（免责声明模板表）
- DisclaimerSignature（免责声明签署表）
- FaqCategory（FAQ分类表）
- FaqItem（FAQ条目表）
- PageConfig（页面配置表）
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---- 模型 ----

class DisclaimerTemplate(Base):
    """免责声明模板表"""

    __tablename__ = "disclaimer_template"
    __table_args__ = (
        Index("idx_dt_site", "site_id"),
        {"comment": "免责声明模板表"},
    )

    title: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="内容"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="内容SHA-256哈希"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
        comment="版本号"
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
    signatures: Mapped[List["DisclaimerSignature"]] = relationship(
        back_populates="template", lazy="noload"
    )


class DisclaimerSignature(Base):
    """免责声明签署表"""

    __tablename__ = "disclaimer_signature"
    __table_args__ = (
        Index("idx_ds_user", "user_id"),
        Index("idx_ds_template", "template_id"),
        Index("idx_ds_order", "order_id"),
        {"comment": "免责声明签署表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("disclaimer_template.id"), nullable=False, comment="模板ID"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="订单ID"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="签署时内容哈希"
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="签署时间"
    )
    signer_openid: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="签署人OpenID"
    )
    signer_ip: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True, comment="签署人IP"
    )

    # 关系
    template: Mapped["DisclaimerTemplate"] = relationship(
        back_populates="signatures"
    )


class FaqCategory(Base):
    """FAQ分类表"""

    __tablename__ = "faq_category"
    __table_args__ = (
        Index("idx_fc_site", "site_id"),
        {"comment": "FAQ分类表"},
    )

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="分类名称"
    )
    code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False,
        comment="分类代码: booking/refund/campsite/traffic/rental/activity/member_card/other"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )

    # 关系
    items: Mapped[List["FaqItem"]] = relationship(
        back_populates="category", lazy="selectin"
    )


class FaqItem(Base):
    """FAQ条目表"""

    __tablename__ = "faq_item"
    __table_args__ = (
        Index("idx_fi_category", "category_id"),
        Index("idx_fi_keywords", "keywords", postgresql_using="gin"),
        Index("idx_fi_site", "site_id"),
        {"comment": "FAQ条目表"},
    )

    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("faq_category.id"), nullable=False, comment="分类ID"
    )
    question: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="问题"
    )
    answer: Mapped[str] = mapped_column(
        Text, nullable=False, comment="回答"
    )
    keywords: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="关键词列表"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序"
    )
    click_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="点击次数"
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
    category: Mapped["FaqCategory"] = relationship(back_populates="items")


class PageConfig(Base):
    """页面配置表"""

    __tablename__ = "page_config"
    __table_args__ = (
        UniqueConstraint("page_key", "site_id", name="uq_page_config_key_site"),
        {"comment": "页面配置表"},
    )

    page_key: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="页面标识: home_banner/home_recommend/home_notice"
    )
    config_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}",
        comment="配置数据"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        server_default="active", comment="状态"
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID"
    )
