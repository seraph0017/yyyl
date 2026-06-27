"""v1.8 add customer service knowledge base

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-27 04:40:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_service_knowledge_article",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
        sa.Column("title", sa.String(length=160), nullable=False, comment="知识标题"),
        sa.Column("content", sa.Text(), nullable=False, comment="知识正文"),
        sa.Column("content_format", sa.String(length=20), server_default="markdown", nullable=False, comment="内容格式"),
        sa.Column("source_type", sa.String(length=20), server_default="manual", nullable=False, comment="来源类型"),
        sa.Column("source_name", sa.String(length=255), nullable=True, comment="来源文件名或来源说明"),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="关键词"),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False, comment="状态"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True, comment="发布时间"),
        sa.Column("created_by", sa.BigInteger(), nullable=True, comment="创建管理员ID"),
        sa.Column("updated_by", sa.BigInteger(), nullable=True, comment="最近更新管理员ID"),
        sa.PrimaryKeyConstraint("id"),
        comment="v1.8 智能客服知识库条目",
    )
    op.create_index("idx_cs_knowledge_site_status", "customer_service_knowledge_article", ["site_id", "status"])
    op.create_index(
        "idx_cs_knowledge_keywords",
        "customer_service_knowledge_article",
        ["keywords"],
        postgresql_using="gin",
    )

    op.create_table(
        "customer_service_ask_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
        sa.Column("channel", sa.String(length=30), server_default="miniapp", nullable=False, comment="来源渠道"),
        sa.Column("user_id", sa.BigInteger(), nullable=True, comment="小程序用户ID"),
        sa.Column("admin_id", sa.BigInteger(), nullable=True, comment="管理端管理员ID"),
        sa.Column("question", sa.Text(), nullable=False, comment="用户问题"),
        sa.Column("answer", sa.Text(), nullable=False, comment="系统回答"),
        sa.Column("matched_article_ids", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), server_default="0", nullable=False, comment="置信度"),
        sa.Column("needs_human", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否人工兜底"),
        sa.Column("feedback", sa.String(length=20), nullable=True, comment="用户反馈"),
        sa.Column("feedback_comment", sa.String(length=500), nullable=True, comment="反馈备注"),
        sa.PrimaryKeyConstraint("id"),
        comment="v1.8 智能客服问答日志",
    )
    op.create_index("idx_cs_ask_log_site_channel", "customer_service_ask_log", ["site_id", "channel"])
    op.create_index("idx_cs_ask_log_site_human", "customer_service_ask_log", ["site_id", "needs_human"])


def downgrade() -> None:
    op.drop_index("idx_cs_ask_log_site_human", table_name="customer_service_ask_log")
    op.drop_index("idx_cs_ask_log_site_channel", table_name="customer_service_ask_log")
    op.drop_table("customer_service_ask_log")
    op.drop_index("idx_cs_knowledge_keywords", table_name="customer_service_knowledge_article")
    op.drop_index("idx_cs_knowledge_site_status", table_name="customer_service_knowledge_article")
    op.drop_table("customer_service_knowledge_article")
