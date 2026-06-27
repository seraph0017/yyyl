"""v1.8 add inventory calendar unique index

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-27 03:05:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_inventory_site_product_sku_date_slot_active"


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _assert_no_duplicate_inventory_rows() -> None:
    duplicate_count = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    site_id,
                    product_id,
                    COALESCE(sku_id, 0) AS sku_key,
                    date,
                    COALESCE(time_slot, '') AS time_slot_key,
                    COUNT(*) AS row_count
                FROM inventory
                WHERE is_deleted = false
                GROUP BY site_id, product_id, COALESCE(sku_id, 0), date, COALESCE(time_slot, '')
                HAVING COUNT(*) > 1
            ) duplicated
            """
        )
    ).scalar()
    if duplicate_count:
        raise RuntimeError(
            "inventory 存在重复的 site/product/sku/date/time_slot 未删除记录，"
            "请先合并或软删除重复库存后再执行 v1.8 唯一索引迁移"
        )


def upgrade() -> None:
    if not _index_exists("inventory", INDEX_NAME):
        _assert_no_duplicate_inventory_rows()
        op.create_index(
            INDEX_NAME,
            "inventory",
            [
                "site_id",
                "product_id",
                sa.text("COALESCE(sku_id, 0)"),
                "date",
                sa.text("COALESCE(time_slot, '')"),
            ],
            unique=True,
            postgresql_where=sa.text("is_deleted = false"),
        )


def downgrade() -> None:
    if _index_exists("inventory", INDEX_NAME):
        op.drop_index(INDEX_NAME, table_name="inventory", if_exists=True)
