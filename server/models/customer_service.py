"""
v1.8 智能客服知识库与问答日志模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CustomerServiceKnowledgeArticle(Base):
    """智能客服知识库条目"""

    __tablename__ = "customer_service_knowledge_article"
    __table_args__ = (
        Index("idx_cs_knowledge_site_status", "site_id", "status"),
        Index("idx_cs_knowledge_keywords", "keywords", postgresql_using="gin"),
        {"comment": "v1.8 智能客服知识库条目"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False, comment="知识标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="知识正文")
    content_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="markdown",
        server_default="markdown",
        comment="内容格式: markdown/text/pdf/docx",
    )
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
        server_default="manual",
        comment="来源类型: manual/txt/md/pdf/docx/faq",
    )
    source_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="来源文件名或来源说明"
    )
    keywords: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="运营维护关键词"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="状态: draft/published/archived",
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建管理员ID")
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="最近更新管理员ID")


class CustomerServiceAskLog(Base):
    """智能客服问答日志"""

    __tablename__ = "customer_service_ask_log"
    __table_args__ = (
        Index("idx_cs_ask_log_site_channel", "site_id", "channel"),
        Index("idx_cs_ask_log_site_human", "site_id", "needs_human"),
        {"comment": "v1.8 智能客服问答日志"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    channel: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="miniapp",
        server_default="miniapp",
        comment="来源渠道: miniapp/admin_preview/enterprise_wechat",
    )
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="小程序用户ID")
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="管理端预览管理员ID")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="用户问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="系统回答")
    matched_article_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]", comment="命中的知识库条目ID"
    )
    source_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]", comment="回答来源引用"
    )
    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0, server_default="0", comment="命中置信度"
    )
    needs_human: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", comment="是否需要人工兜底"
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="用户反馈: helpful/unhelpful"
    )
    feedback_comment: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="反馈备注"
    )
