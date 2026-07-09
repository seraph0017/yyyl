"""v1.9 encrypt user identity id card fields

Revision ID: 4d5e6f708192
Revises: 3c4d5e6f7081
Create Date: 2026-07-09 15:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from utils.security import decrypt_sensitive, encrypt_sensitive, hash_sensitive


revision: str = "4d5e6f708192"
down_revision: Union[str, None] = "3c4d5e6f7081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "user_identity"
HASH_INDEX_NAME = "idx_user_identity_hash"


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


def _add_encrypted_columns() -> None:
    if not _column_exists(TABLE_NAME, "id_card_encrypted"):
        op.add_column(
            TABLE_NAME,
            sa.Column("id_card_encrypted", sa.String(length=256), nullable=True, comment="身份证号（AES-256加密）"),
        )
    if not _column_exists(TABLE_NAME, "id_card_hash"):
        op.add_column(
            TABLE_NAME,
            sa.Column("id_card_hash", sa.String(length=64), nullable=True, comment="身份证号哈希（查询用）"),
        )


def _migrate_plain_id_cards_to_encrypted_columns() -> None:
    if not _column_exists(TABLE_NAME, "id_card"):
        return

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, id_card
            FROM user_identity
            WHERE id_card IS NOT NULL
              AND id_card <> ''
              AND (id_card_encrypted IS NULL OR id_card_encrypted = '')
            """
        )
    ).all()

    for row in rows:
        raw_id_card = (row._mapping["id_card"] or "").strip().upper()
        if not raw_id_card:
            continue
        bind.execute(
            sa.text(
                """
                UPDATE user_identity
                SET id_card_encrypted = :id_card_encrypted,
                    id_card_hash = :id_card_hash
                WHERE id = :identity_id
                """
            ),
            {
                "identity_id": row._mapping["id"],
                "id_card_encrypted": encrypt_sensitive(raw_id_card),
                "id_card_hash": hash_sensitive(raw_id_card),
            },
        )


def _restore_plain_id_cards_from_encrypted_columns() -> None:
    if not _column_exists(TABLE_NAME, "id_card_encrypted"):
        return
    if not _column_exists(TABLE_NAME, "id_card"):
        op.add_column(TABLE_NAME, sa.Column("id_card", sa.String(length=20), nullable=True, comment="身份证号"))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, id_card_encrypted
            FROM user_identity
            WHERE id_card_encrypted IS NOT NULL
              AND id_card_encrypted <> ''
            """
        )
    ).all()

    for row in rows:
        try:
            plain_id_card = decrypt_sensitive(row._mapping["id_card_encrypted"])
        except Exception:
            plain_id_card = None
        if not plain_id_card:
            continue
        bind.execute(
            sa.text("UPDATE user_identity SET id_card = :id_card WHERE id = :identity_id"),
            {"identity_id": row._mapping["id"], "id_card": plain_id_card},
        )


def upgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    _add_encrypted_columns()
    _migrate_plain_id_cards_to_encrypted_columns()

    if not _index_exists(TABLE_NAME, HASH_INDEX_NAME):
        op.create_index(HASH_INDEX_NAME, TABLE_NAME, ["id_card_hash"])

    if _column_exists(TABLE_NAME, "id_card"):
        op.drop_column(TABLE_NAME, "id_card")


def downgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    _restore_plain_id_cards_from_encrypted_columns()

    if _index_exists(TABLE_NAME, HASH_INDEX_NAME):
        op.drop_index(HASH_INDEX_NAME, table_name=TABLE_NAME, if_exists=True)
    if _column_exists(TABLE_NAME, "id_card_hash"):
        op.drop_column(TABLE_NAME, "id_card_hash")
    if _column_exists(TABLE_NAME, "id_card_encrypted"):
        op.drop_column(TABLE_NAME, "id_card_encrypted")
