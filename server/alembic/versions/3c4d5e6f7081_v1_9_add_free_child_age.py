"""v1.9 add free child age to camping extension

Revision ID: 3c4d5e6f7081
Revises: 2b3c4d5e6f70
Create Date: 2026-07-09 13:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c4d5e6f7081"
down_revision: Union[str, None] = "2b3c4d5e6f70"
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
    if not _column_exists("product_ext_camping", "free_child_age"):
        op.add_column(
            "product_ext_camping",
            sa.Column("free_child_age", sa.Integer(), nullable=True, comment="X岁以下儿童免费，空值表示不展示"),
        )


def downgrade() -> None:
    if _column_exists("product_ext_camping", "free_child_age"):
        op.drop_column("product_ext_camping", "free_child_age")
