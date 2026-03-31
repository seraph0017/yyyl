"""add_high_frequency_query_indexes

Revision ID: a3b7c9d1e5f2
Revises: 078ed7222391
Create Date: 2026-03-31 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b7c9d1e5f2"
down_revision: Union[str, None] = "078ed7222391"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Helpers ---

def _safe_create_index(name: str, table: str, columns: list[str], **kw) -> None:
    """Create an index only if it does not already exist."""
    op.create_index(name, table, columns, if_not_exists=True, **kw)


def _safe_drop_index(name: str, table: str) -> None:
    """Drop an index only if it exists."""
    op.drop_index(name, table_name=table, if_exists=True)


# -----------------------------------------------------------------------
# All NEW indexes created by this migration.
# Existing model-level indexes (e.g. idx_order_site, idx_order_user_status)
# are already created in the initial migration and are NOT duplicated here.
# Format: (index_name, table_name, columns)
# -----------------------------------------------------------------------

INDEXES: list[tuple[str, str, list[str]]] = [
    # ── site_id single-column ──
    # Tables with site_id that lack a standalone or leading-column site_id index.
    # Skipped: annual_card (idx_ac_site_status covers it), times_card (idx_tc_site_status),
    #          order (idx_order_site), product (idx_product_site), discount_rule (idx_discount_site),
    #          admin tables (idx_admin_site, idx_ar_site, idx_ol_site), content tables (idx_dt_site, etc.),
    #          camp_map/mini_game (idx_cm_site_status, idx_mg_site_status), expense (idx_er_site, idx_et_site),
    #          performance (idx_pc_site, idx_pr_site), inventory (idx_inv_site_date).
    ("idx_user_site", "user", ["site_id"]),
    ("idx_points_record_site", "points_record", ["site_id"]),
    ("idx_finance_account_site", "finance_account", ["site_id"]),
    ("idx_deposit_record_site", "deposit_record", ["site_id"]),
    ("idx_bundle_item_site", "bundle_item", ["site_id"]),

    # ── status single-column ──
    # Tables with status that lack a standalone status index.
    # Skipped: deposit_record (idx_dr_status), expense_request (idx_er_status),
    #          camp_map (covered by idx_cm_site_status), mini_game (idx_mg_site_status),
    #          annual_card_booking_record (idx_acbr_card_status).
    ("idx_order_status", "order", ["status"]),
    ("idx_product_status", "product", ["status"]),
    ("idx_product_category", "product", ["category"]),
    ("idx_sku_status", "sku", ["status"]),
    ("idx_annual_card_status", "annual_card", ["status"]),
    ("idx_times_card_status", "times_card", ["status"]),
    ("idx_activation_code_status", "activation_code", ["status"]),
    ("idx_pec_status", "points_exchange_config", ["status"]),
    ("idx_ft_status", "finance_transaction", ["status"]),
    ("idx_dt_status", "disclaimer_template", ["status"]),
    ("idx_fi_status", "faq_item", ["status"]),
    ("idx_pc_status", "page_config", ["status"]),
    ("idx_et_status", "expense_type", ["status"]),
    ("idx_admin_user_status", "admin_user", ["status"]),

    # ── user_id single-column ──
    # Skipped: annual_card (idx_ac_user), times_card (idx_tc_user), order (idx_order_user_status),
    #          ticket (idx_ticket_user), notification (idx_noti_user), expense_request (idx_er_user),
    #          points_record (idx_pr_user), disclaimer_signature (idx_ds_user),
    #          user_address (idx_user_address_user), user_identity (idx_user_identity_user).
    # All user_id columns already have indexes — no new single-column user_id indexes needed.

    # ── Composite: order high-frequency queries ──
    ("idx_order_site_status", "order", ["site_id", "status"]),
    ("idx_order_user_created", "order", ["user_id", "created_at"]),

    # ── Composite: product high-frequency queries ──
    ("idx_product_site_status_cat", "product", ["site_id", "status", "category"]),
]


def _all_indexes():
    """Yield all (name, table, columns) tuples."""
    yield from INDEXES


def upgrade() -> None:
    """Add indexes for high-frequency query columns (site_id, status, user_id, composites)."""
    for name, table, columns in _all_indexes():
        _safe_create_index(name, table, columns)


def downgrade() -> None:
    """Drop indexes added by this migration."""
    for name, table, _columns in _all_indexes():
        _safe_drop_index(name, table)
