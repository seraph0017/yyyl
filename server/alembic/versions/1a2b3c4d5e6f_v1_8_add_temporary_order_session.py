"""v1.8 add temporary order session

Revision ID: 1a2b3c4d5e6f
Revises: 0a1b2c3d4e5f
Create Date: 2026-06-27 09:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "0a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "temporary_order_session",
        sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
        sa.Column("session_no", sa.String(length=32), nullable=False, comment="临时会话号"),
        sa.Column("token_hash", sa.String(length=64), nullable=False, comment="扫码认领 Token 摘要"),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False, comment="状态"),
        sa.Column("payment_flow", sa.String(length=30), server_default="customer_scan_qr", nullable=False, comment="收款方式"),
        sa.Column("mode", sa.String(length=30), nullable=False, comment="临时单模式"),
        sa.Column("product_id", sa.BigInteger(), nullable=True, comment="商品ID"),
        sa.Column("sku_id", sa.BigInteger(), nullable=True, comment="SKU ID"),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False, comment="数量"),
        sa.Column("booking_date", sa.Date(), nullable=True, comment="预约日期"),
        sa.Column("time_slot", sa.String(length=20), nullable=True, comment="场次"),
        sa.Column("item_name", sa.String(length=80), nullable=True, comment="自定义收款项名称"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True, comment="自定义收款金额"),
        sa.Column("remark", sa.String(length=200), nullable=True, comment="现场收款备注"),
        sa.Column("created_by_id", sa.BigInteger(), nullable=False, comment="创建人ID"),
        sa.Column("created_by_source", sa.String(length=20), nullable=False, comment="创建来源"),
        sa.Column("order_id", sa.BigInteger(), nullable=True, comment="转化后的正式订单ID"),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=False, comment="会话过期时间"),
        sa.Column("audit_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="现场收款审计数据"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="现场临时订单/收款会话",
    )
    op.create_index("idx_temp_order_session_site_status", "temporary_order_session", ["site_id", "status"])
    op.create_index("idx_temp_order_session_token", "temporary_order_session", ["site_id", "token_hash"])
    op.create_index("idx_temp_order_session_order", "temporary_order_session", ["order_id"])
    op.create_index("uq_temp_order_session_no", "temporary_order_session", ["session_no"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_temp_order_session_no", table_name="temporary_order_session")
    op.drop_index("idx_temp_order_session_order", table_name="temporary_order_session")
    op.drop_index("idx_temp_order_session_token", table_name="temporary_order_session")
    op.drop_index("idx_temp_order_session_site_status", table_name="temporary_order_session")
    op.drop_table("temporary_order_session")
