"""v1.8 add order biz_data

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-27 06:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order",
        sa.Column(
            "biz_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="业务扩展数据，会员卡/临时单等非商品订单使用",
        ),
    )
    op.create_index("uq_ac_order", "annual_card", ["order_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_ac_order", table_name="annual_card")
    op.drop_column("order", "biz_data")
