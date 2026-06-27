"""v1.8 add ticket verify log

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-06-26 21:30:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in set(_inspector().get_table_names())


def upgrade() -> None:
    inspector = _inspector()
    ticket_columns = {column["name"] for column in inspector.get_columns("ticket")} if _table_exists("ticket") else set()
    if "site_id" not in ticket_columns:
        op.add_column(
            "ticket",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
        )
        op.execute(
            """
            UPDATE ticket
            SET site_id = COALESCE("order".site_id, 1)
            FROM "order"
            WHERE ticket.order_id = "order".id
            """
        )
        op.create_index("idx_ticket_site", "ticket", ["site_id"])

    inspector = _inspector()
    ticket_columns = {column["name"] for column in inspector.get_columns("ticket")} if _table_exists("ticket") else set()
    if "qr_token_hash" not in ticket_columns:
        op.add_column(
            "ticket",
            sa.Column("qr_token_hash", sa.String(length=64), nullable=True, comment="二维码Token摘要"),
        )
    if "qr_token" in ticket_columns:
        op.drop_column("ticket", "qr_token")
    index_names = {index["name"] for index in _inspector().get_indexes("ticket")} if _table_exists("ticket") else set()
    if "idx_ticket_qr_token_hash" not in index_names:
        op.create_index("idx_ticket_qr_token_hash", "ticket", ["qr_token_hash"])

    if not _table_exists("ticket_verify_log"):
        op.create_table(
            "ticket_verify_log",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("ticket_id", sa.BigInteger(), nullable=True, comment="票券ID"),
            sa.Column("order_id", sa.BigInteger(), nullable=True, comment="订单ID"),
            sa.Column("order_item_id", sa.BigInteger(), nullable=True, comment="订单项ID"),
            sa.Column("staff_id", sa.BigInteger(), nullable=False, comment="核销员工ID"),
            sa.Column("staff_source", sa.String(length=20), server_default="user", nullable=False, comment="核销员工来源: user/admin"),
            sa.Column("verify_result", sa.String(length=20), nullable=False, comment="核销结果: success/failed/duplicate"),
            sa.Column("failure_reason", sa.String(length=255), nullable=True, comment="失败原因"),
            sa.Column("device_info", sa.String(length=255), nullable=True, comment="设备信息"),
            sa.Column("qr_token_hash", sa.String(length=64), nullable=True, comment="二维码 token 摘要"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.ForeignKeyConstraint(["ticket_id"], ["ticket.id"]),
            sa.ForeignKeyConstraint(["order_id"], ["order.id"]),
            sa.ForeignKeyConstraint(["order_item_id"], ["order_item.id"]),
            sa.PrimaryKeyConstraint("id"),
            comment="v1.8 票券核销日志",
        )
        op.create_index("idx_ticket_verify_log_ticket", "ticket_verify_log", ["ticket_id"])
        op.create_index("idx_ticket_verify_log_staff", "ticket_verify_log", ["staff_id"])
        op.create_index("idx_ticket_verify_log_staff_source", "ticket_verify_log", ["site_id", "staff_source", "staff_id", "created_at"])
        op.create_index("idx_ticket_verify_log_site_created", "ticket_verify_log", ["site_id", "created_at"])
    else:
        log_columns = {column["name"] for column in inspector.get_columns("ticket_verify_log")}
        if "staff_source" not in log_columns:
            op.add_column(
                "ticket_verify_log",
                sa.Column("staff_source", sa.String(length=20), server_default="user", nullable=False, comment="核销员工来源: user/admin"),
            )
        log_indexes = {index["name"] for index in _inspector().get_indexes("ticket_verify_log")}
        if "idx_ticket_verify_log_staff_source" not in log_indexes:
            op.create_index(
                "idx_ticket_verify_log_staff_source",
                "ticket_verify_log",
                ["site_id", "staff_source", "staff_id", "created_at"],
            )


def downgrade() -> None:
    if _table_exists("ticket_verify_log"):
        op.drop_index("idx_ticket_verify_log_staff_source", table_name="ticket_verify_log", if_exists=True)
        op.drop_index("idx_ticket_verify_log_site_created", table_name="ticket_verify_log", if_exists=True)
        op.drop_index("idx_ticket_verify_log_staff", table_name="ticket_verify_log", if_exists=True)
        op.drop_index("idx_ticket_verify_log_ticket", table_name="ticket_verify_log", if_exists=True)
        op.drop_table("ticket_verify_log")
    if _table_exists("ticket"):
        ticket_columns = {column["name"] for column in _inspector().get_columns("ticket")}
        index_names = {index["name"] for index in _inspector().get_indexes("ticket")}
        if "idx_ticket_qr_token_hash" in index_names:
            op.drop_index("idx_ticket_qr_token_hash", table_name="ticket")
        if "qr_token_hash" in ticket_columns:
            op.drop_column("ticket", "qr_token_hash")
        if "site_id" in ticket_columns:
            op.drop_index("idx_ticket_site", table_name="ticket", if_exists=True)
            op.drop_column("ticket", "site_id")
