import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from middleware import auth


class AuthMiddlewareStaffPrincipalTest(unittest.IsolatedAsyncioTestCase):
    async def test_staff_principal_accepts_miniapp_staff_user_token(self):
        user = SimpleNamespace(
            id=7,
            site_id=2,
            role="staff",
            status="active",
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=Mock(return_value=user))
            )
        )

        with patch.object(auth, "verify_token", return_value={"token_type": "access", "sub": "7", "role": "staff"}):
            principal = await auth.get_current_staff_principal(token="staff-token", db=db)

        self.assertEqual(principal.id, 7)
        self.assertEqual(principal.site_id, 2)
        self.assertEqual(principal.role, "staff")
        self.assertEqual(principal.source, "user")

    async def test_staff_principal_accepts_admin_staff_token(self):
        admin = SimpleNamespace(
            id=9,
            site_id=1,
            status="active",
            role=SimpleNamespace(role_code="staff"),
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=Mock(return_value=admin))
            )
        )

        with patch.object(auth, "verify_token", return_value={"token_type": "access", "sub": "admin:9", "role": "staff"}):
            principal = await auth.get_current_staff_principal(token="admin-token", db=db)

        self.assertEqual(principal.id, 9)
        self.assertEqual(principal.site_id, 1)
        self.assertEqual(principal.role, "staff")
        self.assertEqual(principal.source, "admin")

    async def test_staff_principal_rechecks_admin_database_role(self):
        admin = SimpleNamespace(
            id=9,
            site_id=1,
            status="active",
            role=SimpleNamespace(role_code="viewer"),
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=Mock(return_value=admin))
            )
        )

        with patch.object(auth, "verify_token", return_value={"token_type": "access", "sub": "admin:9", "role": "staff"}):
            with self.assertRaises(HTTPException) as ctx:
                await auth.get_current_staff_principal(token="admin-token", db=db)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], 40302)

    async def test_staff_principal_rejects_normal_user_token(self):
        db = SimpleNamespace()

        with patch.object(auth, "verify_token", return_value={"token_type": "access", "sub": "7", "role": "user"}):
            with self.assertRaises(HTTPException) as ctx:
                await auth.get_current_staff_principal(token="user-token", db=db)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], 40302)


if __name__ == "__main__":
    unittest.main()
