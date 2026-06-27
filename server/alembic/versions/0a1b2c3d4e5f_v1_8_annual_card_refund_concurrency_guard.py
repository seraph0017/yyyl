"""v1.8 annual card and refund concurrency guard

Revision ID: 0a1b2c3d4e5f
Revises: e5f6a7b8c9d0
Create Date: 2026-06-27 08:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assert_no_duplicate_pending_annual_orders() -> None:
    rows = op.get_bind().execute(sa.text("""
        SELECT user_id, site_id, COUNT(*) AS duplicate_count
        FROM "order"
        WHERE order_type = 'annual_card'
          AND status = 'pending_payment'
          AND payment_status = 'unpaid'
          AND is_deleted = false
        GROUP BY user_id, site_id
        HAVING COUNT(*) > 1
    """)).fetchall()
    if rows:
        sample = ", ".join(
            f"user_id={row.user_id}, site_id={row.site_id}, count={row.duplicate_count}"
            for row in rows[:5]
        )
        raise RuntimeError(f"存在重复年卡待支付订单，请先取消或合并后再执行迁移：{sample}")


def _assert_no_duplicate_active_refunds() -> None:
    rows = op.get_bind().execute(sa.text("""
        SELECT order_id, COUNT(*) AS duplicate_count
        FROM refund_record
        WHERE status IN ('pending', 'processing')
          AND is_deleted = false
        GROUP BY order_id
        HAVING COUNT(*) > 1
    """)).fetchall()
    if rows:
        sample = ", ".join(
            f"order_id={row.order_id}, count={row.duplicate_count}"
            for row in rows[:5]
        )
        raise RuntimeError(f"存在重复进行中退款记录，请先处理后再执行迁移：{sample}")


def _assert_no_duplicate_refund_transactions() -> None:
    rows = op.get_bind().execute(sa.text("""
        SELECT refund_record_id, COUNT(*) AS duplicate_count
        FROM finance_transaction
        WHERE refund_record_id IS NOT NULL
          AND type = 'refund'
          AND is_deleted = false
        GROUP BY refund_record_id
        HAVING COUNT(*) > 1
    """)).fetchall()
    if rows:
        sample = ", ".join(
            f"refund_record_id={row.refund_record_id}, count={row.duplicate_count}"
            for row in rows[:5]
        )
        raise RuntimeError(f"存在重复退款财务流水，请先审计处理后再执行迁移：{sample}")


def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE "order"
        SET status = 'cancelled',
            remark = COALESCE(NULLIF(remark, ''), '系统自动取消：年卡订单支付超时')
        WHERE order_type = 'annual_card'
          AND status = 'pending_payment'
          AND payment_status = 'unpaid'
          AND expire_at <= now()
          AND is_deleted = false
    """))
    _assert_no_duplicate_pending_annual_orders()
    _assert_no_duplicate_active_refunds()
    _assert_no_duplicate_refund_transactions()

    op.create_index(
        "uq_order_annual_pending_active",
        "order",
        ["user_id", "site_id"],
        unique=True,
        postgresql_where=sa.text(
            "order_type = 'annual_card' "
            "AND status = 'pending_payment' "
            "AND payment_status = 'unpaid' "
            "AND is_deleted = false"
        ),
    )
    op.create_index(
        "uq_refund_record_active_order",
        "refund_record",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'processing') AND is_deleted = false"),
    )
    op.create_index(
        "uq_ft_refund_record",
        "finance_transaction",
        ["refund_record_id"],
        unique=True,
        postgresql_where=sa.text(
            "refund_record_id IS NOT NULL AND type = 'refund' AND is_deleted = false"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_ft_refund_record", table_name="finance_transaction")
    op.drop_index("uq_refund_record_active_order", table_name="refund_record")
    op.drop_index("uq_order_annual_pending_active", table_name="order")
