"""v1.8 add refund inventory release idempotency flag

Revision ID: f6a7b8c9d0e1
Revises: e4f5a6b7c8d9
Create Date: 2026-06-26 12:10:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in set(_inspector().get_table_names())


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("refund_record", "inventory_released"):
        op.add_column(
            "refund_record",
            sa.Column(
                "inventory_released",
                sa.Boolean(),
                server_default="false",
                nullable=False,
                comment="库存是否已实际释放，保障退款回补幂等",
            ),
        )


def downgrade() -> None:
    if _column_exists("refund_record", "inventory_released"):
        op.drop_column("refund_record", "inventory_released")
