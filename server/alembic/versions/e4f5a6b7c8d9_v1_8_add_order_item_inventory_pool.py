"""v1.8 add order item inventory pool reference

Revision ID: e4f5a6b7c8d9
Revises: d2e3f4a5b6c7
Create Date: 2026-06-26 11:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
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


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {index["name"] for index in _inspector().get_indexes(table_name)}


def _foreign_key_exists(table_name: str, fk_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return fk_name in {fk["name"] for fk in _inspector().get_foreign_keys(table_name)}


def upgrade() -> None:
    if not _column_exists("order_item", "inventory_pool_id"):
        op.add_column(
            "order_item",
            sa.Column(
                "inventory_pool_id",
                sa.BigInteger(),
                nullable=True,
                comment="v1.8 订单锁定的共享库存池ID",
            ),
        )
    if not _foreign_key_exists("order_item", "fk_order_item_inventory_pool"):
        op.create_foreign_key(
            "fk_order_item_inventory_pool",
            "order_item",
            "inventory_pool",
            ["inventory_pool_id"],
            ["id"],
        )
    if not _index_exists("order_item", "idx_order_item_inventory_pool"):
        op.create_index("idx_order_item_inventory_pool", "order_item", ["inventory_pool_id"])


def downgrade() -> None:
    if _index_exists("order_item", "idx_order_item_inventory_pool"):
        op.drop_index("idx_order_item_inventory_pool", table_name="order_item", if_exists=True)
    if _foreign_key_exists("order_item", "fk_order_item_inventory_pool"):
        op.drop_constraint("fk_order_item_inventory_pool", "order_item", type_="foreignkey")
    if _column_exists("order_item", "inventory_pool_id"):
        op.drop_column("order_item", "inventory_pool_id")
