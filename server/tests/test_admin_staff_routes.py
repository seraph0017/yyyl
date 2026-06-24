import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from routers import admin as admin_router
from schemas.admin import AdminUserCreate


class AdminStaffRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_staff_rejects_non_super_admin(self):
        db = SimpleNamespace()
        admin = SimpleNamespace(role=SimpleNamespace(role_code="admin"))

        with self.assertRaises(HTTPException) as ctx:
            await admin_router.create_staff(
                AdminUserCreate(
                    username="ops_admin",
                    password="secret123",
                    real_name="运营管理员",
                    phone="13800000000",
                    role_id=2,
                ),
                db=db,
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_create_staff_uses_bcrypt_hash_for_super_admin(self):
        added = []
        db = SimpleNamespace(
            add=lambda obj: added.append(obj),
            commit=AsyncMock(),
            refresh=AsyncMock(side_effect=lambda obj: setattr(obj, "id", 99)),
            execute=AsyncMock(
                side_effect=[
                    SimpleNamespace(
                        scalar_one_or_none=Mock(
                            return_value=SimpleNamespace(id=2, role_code="admin")
                        )
                    ),
                    SimpleNamespace(scalar_one_or_none=Mock(return_value=None)),
                ]
            ),
        )
        admin = SimpleNamespace(role=SimpleNamespace(role_code="super_admin"))

        with patch.object(admin_router, "hash_password", return_value="bcrypt-hash") as hash_password:
            result = await admin_router.create_staff(
                AdminUserCreate(
                    username="ops_admin",
                    password="secret123",
                    real_name="运营管理员",
                    phone="13800000000",
                    role_id=2,
                ),
                db=db,
                admin=admin,
            )

        hash_password.assert_called_once_with("secret123")
        self.assertEqual(len(added), 1)
        created = added[0]
        self.assertEqual(created.username, "ops_admin")
        self.assertEqual(created.password_hash, "bcrypt-hash")
        self.assertEqual(created.real_name, "运营管理员")
        self.assertEqual(created.phone, "13800000000")
        self.assertEqual(created.role_id, 2)
        self.assertEqual(result.data["id"], 99)

    async def test_create_staff_rejects_super_admin_role(self):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=Mock(
                        return_value=SimpleNamespace(id=1, role_code="super_admin")
                    )
                )
            )
        )
        admin = SimpleNamespace(role=SimpleNamespace(role_code="super_admin"))

        with self.assertRaises(HTTPException) as ctx:
            await admin_router.create_staff(
                AdminUserCreate(
                    username="root2",
                    password="secret123",
                    real_name="超级管理员2",
                    role_id=1,
                ),
                db=db,
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "SUPER_ADMIN_CREATE_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
