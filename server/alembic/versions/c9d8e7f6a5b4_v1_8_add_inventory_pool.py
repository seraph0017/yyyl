"""v1.8 add inventory pool

Revision ID: c9d8e7f6a5b4
Revises: b7e2f8a9c1d4
Create Date: 2026-06-26 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "b7e2f8a9c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return table_name in set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _table_exists("inventory_pool"):
        op.create_table(
            "inventory_pool",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("pool_code", sa.String(length=64), nullable=False, comment="库存池编码，同营地唯一"),
            sa.Column("name", sa.String(length=128), nullable=False, comment="库存池名称"),
            sa.Column("pool_type", sa.String(length=30), server_default="generic", nullable=False, comment="库存池类型"),
            sa.Column("total", sa.Integer(), server_default="0", nullable=False, comment="总库存"),
            sa.Column("available", sa.Integer(), server_default="0", nullable=False, comment="可用库存"),
            sa.Column("locked", sa.Integer(), server_default="0", nullable=False, comment="锁定库存"),
            sa.Column("sold", sa.Integer(), server_default="0", nullable=False, comment="已售库存"),
            sa.Column("status", sa.String(length=20), server_default="active", nullable=False, comment="状态"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.CheckConstraint("total >= 0", name="ck_inventory_pool_total_non_negative"),
            sa.CheckConstraint("available >= 0", name="ck_inventory_pool_available_non_negative"),
            sa.CheckConstraint("locked >= 0", name="ck_inventory_pool_locked_non_negative"),
            sa.CheckConstraint("sold >= 0", name="ck_inventory_pool_sold_non_negative"),
            sa.CheckConstraint("available + locked + sold = total", name="ck_inventory_pool_quantity_sum"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("site_id", "pool_code", name="uq_inventory_pool_site_code"),
            comment="v1.8 跨商品共享库存池",
        )
        op.create_index("idx_inventory_pool_site_status", "inventory_pool", ["site_id", "status"])

    if not _table_exists("inventory_pool_binding"):
        op.create_table(
            "inventory_pool_binding",
            sa.Column("inventory_pool_id", sa.BigInteger(), nullable=False, comment="库存池ID"),
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("product_id", sa.BigInteger(), nullable=True, comment="商品ID"),
            sa.Column("sku_id", sa.BigInteger(), nullable=True, comment="SKU ID"),
            sa.Column("activity_session_id", sa.BigInteger(), nullable=True, comment="活动场次ID"),
            sa.Column("rental_asset_id", sa.BigInteger(), nullable=True, comment="租赁资产ID"),
            sa.Column("priority", sa.Integer(), server_default="100", nullable=False, comment="匹配优先级"),
            sa.Column("status", sa.String(length=20), server_default="active", nullable=False, comment="状态"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.ForeignKeyConstraint(["inventory_pool_id"], ["inventory_pool.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["sku_id"], ["sku.id"]),
            sa.CheckConstraint(
                "("
                "(CASE WHEN product_id IS NOT NULL THEN 1 ELSE 0 END) + "
                "(CASE WHEN sku_id IS NOT NULL THEN 1 ELSE 0 END) + "
                "(CASE WHEN activity_session_id IS NOT NULL THEN 1 ELSE 0 END) + "
                "(CASE WHEN rental_asset_id IS NOT NULL THEN 1 ELSE 0 END)"
                ") = 1",
                name="ck_inventory_pool_binding_exactly_one_target",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="v1.8 库存池绑定关系",
        )
        op.create_index("idx_inventory_pool_binding_pool", "inventory_pool_binding", ["inventory_pool_id"])
        op.create_index("idx_inventory_pool_binding_site_status", "inventory_pool_binding", ["site_id", "status"])
        op.create_index("idx_inventory_pool_binding_product", "inventory_pool_binding", ["product_id"])
        op.create_index("idx_inventory_pool_binding_sku", "inventory_pool_binding", ["sku_id"])
        op.create_index("idx_inventory_pool_binding_activity", "inventory_pool_binding", ["activity_session_id"])
        op.create_index("idx_inventory_pool_binding_rental", "inventory_pool_binding", ["rental_asset_id"])
        op.create_index(
            "uq_inventory_pool_binding_active_product",
            "inventory_pool_binding",
            ["site_id", "product_id"],
            unique=True,
            postgresql_where=sa.text("product_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        )
        op.create_index(
            "uq_inventory_pool_binding_active_sku",
            "inventory_pool_binding",
            ["site_id", "sku_id"],
            unique=True,
            postgresql_where=sa.text("sku_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        )
        op.create_index(
            "uq_inventory_pool_binding_active_activity",
            "inventory_pool_binding",
            ["site_id", "activity_session_id"],
            unique=True,
            postgresql_where=sa.text("activity_session_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        )
        op.create_index(
            "uq_inventory_pool_binding_active_rental",
            "inventory_pool_binding",
            ["site_id", "rental_asset_id"],
            unique=True,
            postgresql_where=sa.text("rental_asset_id IS NOT NULL AND status = 'active' AND is_deleted = false"),
        )


def downgrade() -> None:
    if _table_exists("inventory_pool_binding"):
        op.drop_index("uq_inventory_pool_binding_active_rental", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("uq_inventory_pool_binding_active_activity", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("uq_inventory_pool_binding_active_sku", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("uq_inventory_pool_binding_active_product", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("idx_inventory_pool_binding_rental", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("idx_inventory_pool_binding_activity", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("idx_inventory_pool_binding_sku", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("idx_inventory_pool_binding_product", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("idx_inventory_pool_binding_site_status", table_name="inventory_pool_binding", if_exists=True)
        op.drop_index("idx_inventory_pool_binding_pool", table_name="inventory_pool_binding", if_exists=True)
        op.drop_table("inventory_pool_binding")

    if _table_exists("inventory_pool"):
        op.drop_index("idx_inventory_pool_site_status", table_name="inventory_pool", if_exists=True)
        op.drop_table("inventory_pool")
