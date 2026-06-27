import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from services import auth_service


class AuthServicePhoneLoginTest(unittest.IsolatedAsyncioTestCase):
    async def test_phone_login_fetches_wechat_phone_and_binds_user(self):
        user = SimpleNamespace(
            id=7,
            openid="openid-7",
            nickname="露营用户",
            avatar_url=None,
            phone=None,
            role="user",
            is_member=False,
            member_level="normal",
            points_balance=0,
            status="active",
            last_login_at=None,
            created_at=datetime(2026, 6, 26),
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=Mock(return_value=user))
            ),
            flush=AsyncMock(),
        )

        with (
            patch.object(auth_service, "_code2session", AsyncMock(return_value=("openid-7", "session-key"))) as code2session,
            patch.object(auth_service, "_get_phone_number", AsyncMock(return_value="13800000000")) as get_phone,
        ):
            result = await auth_service.phone_login("login-code", "phone-code", db, site_id=2)

        code2session.assert_awaited_once_with("login-code", 2)
        get_phone.assert_awaited_once_with("phone-code", site_id=2)
        self.assertEqual(user.phone, "13800000000")
        self.assertIsNotNone(user.last_login_at)
        self.assertEqual(result["user_info"]["phone"], "138****0000")
        self.assertEqual(result["user_info"]["id"], 7)
        db.flush.assert_awaited_once()

    async def test_phone_login_rejects_wechat_response_without_phone(self):
        db = SimpleNamespace()

        with patch.object(auth_service, "_get_wechat_access_token", AsyncMock(return_value="access-token")):
            with patch.object(
                auth_service.httpx.AsyncClient,
                "post",
                AsyncMock(return_value=SimpleNamespace(json=Mock(return_value={"errcode": 0, "phone_info": {}}))),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    await auth_service._get_phone_number("phone-code", site_id=1)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.detail["code"], 50003)
        self.assertIn("手机号", ctx.exception.detail["message"])


if __name__ == "__main__":
    unittest.main()
