"""v1.8 add map analytics

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-26 22:10:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in set(_inspector().get_table_names())


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def upgrade() -> None:
    zone_columns = _column_names("camp_map_zone")
    if "link_type" not in zone_columns:
        op.add_column(
            "camp_map_zone",
            sa.Column("link_type", sa.String(length=20), nullable=True, comment="热区链接类型: product/cms/h5/none"),
        )
    if "link_target" not in zone_columns:
        op.add_column(
            "camp_map_zone",
            sa.Column("link_target", sa.String(length=500), nullable=True, comment="热区链接目标"),
        )
    if "link_label" not in zone_columns:
        op.add_column(
            "camp_map_zone",
            sa.Column("link_label", sa.String(length=50), nullable=True, comment="热区链接按钮文案"),
        )
    if "click_count" not in zone_columns:
        op.add_column(
            "camp_map_zone",
            sa.Column("click_count", sa.Integer(), server_default="0", nullable=False, comment="点击次数"),
        )

    if not _table_exists("page_view_stat"):
        op.create_table(
            "page_view_stat",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("page_key", sa.String(length=100), nullable=False, comment="页面标识"),
            sa.Column("page_title", sa.String(length=100), nullable=True, comment="页面标题"),
            sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
            sa.Column("view_count", sa.Integer(), server_default="0", nullable=False, comment="浏览次数"),
            sa.Column("user_count", sa.Integer(), server_default="0", nullable=False, comment="登录用户访问次数"),
            sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True, comment="最近访问时间"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.PrimaryKeyConstraint("id"),
            comment="v1.8 页面浏览统计聚合表",
        )
        op.create_index(
            "idx_pvs_site_page_date",
            "page_view_stat",
            ["site_id", "page_key", "stat_date"],
            unique=True,
        )
        op.create_index("idx_pvs_site_date", "page_view_stat", ["site_id", "stat_date"])


def downgrade() -> None:
    if _table_exists("page_view_stat"):
        op.drop_index("idx_pvs_site_date", table_name="page_view_stat", if_exists=True)
        op.drop_index("idx_pvs_site_page_date", table_name="page_view_stat", if_exists=True)
        op.drop_table("page_view_stat")

    zone_columns = _column_names("camp_map_zone")
    for column_name in ("click_count", "link_label", "link_target", "link_type"):
        if column_name in zone_columns:
            op.drop_column("camp_map_zone", column_name)
