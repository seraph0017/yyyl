import unittest
from datetime import datetime, timezone
from pathlib import Path

from models.user import UserIdentity
from schemas.user import UserIdentityResponse
from utils.security import hash_sensitive, mask_id_card


class UserIdentitySensitiveFieldsTest(unittest.TestCase):
    def test_id_card_virtual_field_encrypts_hashes_and_response_masks(self):
        raw_id_card = "11010119900101123x"
        normalized_id_card = "11010119900101123X"

        identity = UserIdentity(
            id=10,
            user_id=1,
            name="张三",
            id_card=raw_id_card,
            phone="13800138000",
            is_self=False,
            is_default=True,
            created_at=datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
        )

        self.assertIsNotNone(identity.id_card_encrypted)
        self.assertNotEqual(identity.id_card_encrypted, raw_id_card)
        self.assertEqual(identity.id_card_hash, hash_sensitive(normalized_id_card))
        self.assertEqual(identity.id_card, normalized_id_card)
        self.assertEqual(identity.id_card_masked, mask_id_card(normalized_id_card))

        response = UserIdentityResponse.model_validate(identity)
        self.assertEqual(response.id_card_masked, mask_id_card(normalized_id_card))
        self.assertEqual(response.phone, "138****8000")

    def test_user_identity_constructor_accepts_virtual_id_card_keyword(self):
        identity = UserIdentity(
            user_id=1,
            name="李四",
            id_card="110101199001011234",
            phone="13800138000",
        )

        self.assertIsNotNone(identity.id_card_encrypted)
        self.assertEqual(identity.id_card, "110101199001011234")

    def test_clearing_id_card_clears_encrypted_and_hash_values(self):
        identity = UserIdentity(user_id=1, id_card="110101199001011234")

        identity.id_card = ""

        self.assertIsNone(identity.id_card)
        self.assertIsNone(identity.id_card_encrypted)
        self.assertIsNone(identity.id_card_hash)
        self.assertIsNone(identity.id_card_masked)

    def test_user_identity_encrypted_columns_have_alembic_migration(self):
        versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
        migration_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in versions_dir.glob("*.py")
            if path.name != "__init__.py"
        )

        self.assertIn("id_card_encrypted", migration_sources)
        self.assertIn("id_card_hash", migration_sources)
        self.assertIn('"user_identity"', migration_sources)
        self.assertIn('"idx_user_identity_hash"', migration_sources)
        self.assertIn("encrypt_sensitive", migration_sources)
        self.assertIn("hash_sensitive", migration_sources)


if __name__ == "__main__":
    unittest.main()
