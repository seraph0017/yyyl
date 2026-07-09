import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from routers import admin as admin_router
from routers import expenses as expenses_router
from routers import finance as finance_router
from routers import orders as orders_router
from schemas.admin import OperationPasswordUpdateRequest
from utils.security import hash_password, verify_password


class AdminConfirmRouteTest(unittest.IsolatedAsyncioTestCase):
    def make_admin(self, *, role_code="super_admin", site_id=2):
        return SimpleNamespace(
            id=9,
            site_id=site_id,
            role=SimpleNamespace(role_code=role_code),
            operation_password_hash=hash_password("123456"),
        )

    async def test_update_operation_password_requires_old_password_when_already_set(self):
        admin = self.make_admin()
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        with self.assertRaises(HTTPException) as missing_ctx:
            await admin_router.update_operation_password(
                OperationPasswordUpdateRequest(password="654321"),
                request=request,
                db=SimpleNamespace(flush=AsyncMock()),
                admin=admin,
            )

        self.assertEqual(missing_ctx.exception.status_code, 403)
        self.assertIn("旧操作密码", str(missing_ctx.exception.detail))

        with self.assertRaises(HTTPException) as wrong_ctx:
            await admin_router.update_operation_password(
                OperationPasswordUpdateRequest(password="654321", old_password="111111"),
                request=request,
                db=SimpleNamespace(flush=AsyncMock()),
                admin=admin,
            )

        self.assertEqual(wrong_ctx.exception.status_code, 403)
        self.assertIn("旧操作密码错误", str(wrong_ctx.exception.detail))

    async def test_update_operation_password_writes_bcrypt_hash_after_old_password(self):
        admin = self.make_admin()
        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        db = SimpleNamespace(flush=AsyncMock())

        result = await admin_router.update_operation_password(
            OperationPasswordUpdateRequest(password="654321", old_password="123456"),
            request=request,
            db=db,
            admin=admin,
        )

        self.assertTrue(result.data["updated"])
        self.assertEqual(result.data["site_id"], 2)
        self.assertNotEqual(admin.operation_password_hash, "654321")
        self.assertTrue(verify_password("654321", admin.operation_password_hash))
        self.assertTrue(admin.operation_password_hash.startswith("$2"))
        db.flush.assert_awaited_once()

    async def test_update_operation_password_allows_first_setup_without_old_password(self):
        admin = self.make_admin()
        admin.operation_password_hash = None
        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        db = SimpleNamespace(flush=AsyncMock())

        result = await admin_router.update_operation_password(
            OperationPasswordUpdateRequest(password="654321"),
            request=request,
            db=db,
            admin=admin,
        )

        self.assertTrue(result.data["updated"])
        self.assertTrue(verify_password("654321", admin.operation_password_hash))
        db.flush.assert_awaited_once()

    def test_operation_password_schema_rejects_non_ascii_digits(self):
        with self.assertRaises(ValidationError):
            OperationPasswordUpdateRequest(password="１２３４５６")

    async def test_update_operation_password_requires_super_admin(self):
        admin = self.make_admin(role_code="admin")
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        with self.assertRaises(HTTPException) as ctx:
            await admin_router.update_operation_password(
                OperationPasswordUpdateRequest(password="654321"),
                request=request,
                db=SimpleNamespace(flush=AsyncMock()),
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_update_operation_password_requires_explicit_site_header(self):
        admin = self.make_admin()

        with self.assertRaises(HTTPException) as ctx:
            await admin_router.update_operation_password(
                OperationPasswordUpdateRequest(password="654321"),
                request=SimpleNamespace(headers={}),
                db=SimpleNamespace(flush=AsyncMock()),
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("X-Site-Id", str(ctx.exception.detail))

    async def test_verify_operation_password_uses_bcrypt_and_returns_bound_token(self):
        admin = self.make_admin()
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        result = await admin_router.verify_operation_password(
            {
                "password": "123456",
                "action": "refund:approve:88",
                "request_hash": "hash-ok",
            },
            request=request,
            db=SimpleNamespace(),
            admin=admin,
        )

        self.assertTrue(result.data["verified"])
        self.assertEqual(result.data["action"], "refund:approve:88")
        self.assertIn("confirm_token", result.data)
        self.assertGreater(len(result.data["confirm_token"]), 20)

    async def test_verify_operation_password_requires_super_admin(self):
        admin = self.make_admin(role_code="admin")
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        with self.assertRaises(HTTPException) as ctx:
            await admin_router.verify_operation_password(
                {"password": "123456", "action": "inventory_pool:create"},
                request=request,
                db=SimpleNamespace(),
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_verify_operation_password_requires_explicit_site_header_and_request_hash(self):
        admin = self.make_admin()

        for headers in ({}, {"X-Site-Id": ""}, {"X-Site-Id": "abc"}, {"X-Site-Id": "9"}):
            with self.subTest(headers=headers):
                with self.assertRaises(HTTPException) as ctx:
                    await admin_router.verify_operation_password(
                        {
                            "password": "123456",
                            "action": "inventory_pool:create",
                            "request_hash": "hash-ok",
                        },
                        request=SimpleNamespace(headers=headers),
                        db=SimpleNamespace(),
                        admin=admin,
                    )
                self.assertEqual(ctx.exception.status_code, 400)
                self.assertIn("X-Site-Id", str(ctx.exception.detail))

        with self.assertRaises(HTTPException) as ctx_hash:
            await admin_router.verify_operation_password(
                {
                    "password": "123456",
                    "action": "inventory_pool:create",
                    "request_hash": "",
                },
                request=SimpleNamespace(headers={"X-Site-Id": "2"}),
                db=SimpleNamespace(),
                admin=admin,
            )

        self.assertEqual(ctx_hash.exception.status_code, 400)
        self.assertIn("request_hash", str(ctx_hash.exception.detail))

    async def test_high_risk_confirm_token_is_required_and_bound(self):
        admin = self.make_admin()
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        with self.assertRaises(HTTPException) as ctx:
            admin_router._require_high_risk_confirm(
                request,
                admin,
                action="inventory_pool:create",
                request_hash="abc123",
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("二次确认", str(ctx.exception.detail))

        token = admin_router._build_confirm_token(
            admin,
            action="inventory_pool:create",
            request_hash="abc123",
        )
        request.headers["X-Confirm-Token"] = token
        admin_router._require_high_risk_confirm(
            request,
            admin,
            action="inventory_pool:create",
            request_hash="abc123",
        )

        with self.assertRaises(HTTPException):
            admin_router._require_high_risk_confirm(
                request,
                admin,
                action="enterprise_wechat:update",
                request_hash="abc123",
            )

    async def test_high_risk_confirm_requires_explicit_site_header(self):
        admin = self.make_admin()
        token = admin_router._build_confirm_token(
            admin,
            action="inventory_pool:create",
            request_hash="abc123",
            site_id=2,
        )

        for headers in ({}, {"X-Site-Id": ""}, {"X-Site-Id": "abc"}, {"X-Site-Id": "9"}):
            with self.subTest(headers=headers):
                request = SimpleNamespace(headers={**headers, "X-Confirm-Token": token})
                with self.assertRaises(HTTPException) as ctx:
                    admin_router._require_high_risk_confirm(
                        request,
                        admin,
                        action="inventory_pool:create",
                        request_hash="abc123",
                    )
                self.assertEqual(ctx.exception.status_code, 400)
                self.assertIn("X-Site-Id", str(ctx.exception.detail))

    async def test_high_risk_confirm_requires_request_hash_and_target_site_match(self):
        admin = self.make_admin(site_id=1)
        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        body = {"name": "A", "total": 10, "available": 8, "locked": 1, "sold": 1}
        request_hash = admin_router._hash_high_risk_body(body)

        token = admin_router._build_confirm_token(
            admin,
            action="inventory_pool:create",
            request_hash=request_hash,
            site_id=2,
        )
        request.headers["X-Confirm-Token"] = token
        admin_router._require_high_risk_confirm(
            request,
            admin,
            action="inventory_pool:create",
            request_hash=request_hash,
        )

        with self.assertRaises(HTTPException) as ctx_hash:
            admin_router._require_high_risk_confirm(
                request,
                admin,
                action="inventory_pool:create",
                request_hash=admin_router._hash_high_risk_body({**body, "total": 11}),
            )
        self.assertIn("请求内容", str(ctx_hash.exception.detail))

        no_hash_token = admin_router._build_confirm_token(
            admin,
            action="inventory_pool:create",
            request_hash="",
            site_id=2,
        )
        request.headers["X-Confirm-Token"] = no_hash_token
        with self.assertRaises(HTTPException) as ctx_empty:
            admin_router._require_high_risk_confirm(
                request,
                admin,
                action="inventory_pool:create",
                request_hash="",
            )
        self.assertIn("请求内容", str(ctx_empty.exception.detail))

        wrong_site_token = admin_router._build_confirm_token(
            admin,
            action="inventory_pool:create",
            request_hash=request_hash,
            site_id=1,
        )
        request.headers["X-Confirm-Token"] = wrong_site_token
        with self.assertRaises(HTTPException) as ctx_site:
            admin_router._require_high_risk_confirm(
                request,
                admin,
                action="inventory_pool:create",
                request_hash=request_hash,
            )
        self.assertIn("不匹配", str(ctx_site.exception.detail))

    async def test_verify_confirm_code_does_not_accept_hash_prefix(self):
        password_hash = hash_password("654321")
        admin = SimpleNamespace(
            id=9,
            site_id=2,
            role=SimpleNamespace(role_code="super_admin"),
            operation_password_hash=password_hash,
        )
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        with self.assertRaises(HTTPException) as ctx:
            await admin_router.verify_confirm_code(
                {"code": password_hash[:6], "action": "export:orders", "request_hash": "hash-ok"},
                request=request,
                db=SimpleNamespace(),
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("确认码错误", str(ctx.exception.detail))

    async def test_verify_confirm_code_requires_explicit_site_header_and_request_hash(self):
        admin = self.make_admin()

        with self.assertRaises(HTTPException) as ctx_site:
            await admin_router.verify_confirm_code(
                {
                    "code": "123456",
                    "action": "inventory_pool:create",
                    "request_hash": "hash-ok",
                },
                request=SimpleNamespace(headers={}),
                db=SimpleNamespace(),
                admin=admin,
            )

        self.assertEqual(ctx_site.exception.status_code, 400)
        self.assertIn("X-Site-Id", str(ctx_site.exception.detail))

        with self.assertRaises(HTTPException) as ctx_hash:
            await admin_router.verify_confirm_code(
                {
                    "code": "123456",
                    "action": "inventory_pool:create",
                    "request_hash": "",
                },
                request=SimpleNamespace(headers={"X-Site-Id": "2"}),
                db=SimpleNamespace(),
                admin=admin,
            )

        self.assertEqual(ctx_hash.exception.status_code, 400)
        self.assertIn("request_hash", str(ctx_hash.exception.detail))

    async def test_sensitive_order_export_confirm_token_matches_admin_token_shape(self):
        admin = self.make_admin(site_id=1)
        payload = {
            "filters": {"status": "paid"},
            "file_format": "xlsx",
            "include_sensitive": True,
        }
        token = admin_router._build_confirm_token(
            admin,
            action="orders:export_sensitive",
            request_hash=orders_router._stable_request_hash(payload),
            site_id=1,
        )

        orders_router._require_confirm_token(
            admin=admin,
            site_id=1,
            action="orders:export_sensitive",
            payload=payload,
            confirm_token=token,
        )

        with self.assertRaises(HTTPException) as ctx:
            orders_router._require_confirm_token(
                admin=admin,
                site_id=1,
                action="orders:export_sensitive",
                payload={**payload, "file_format": "csv"},
                confirm_token=token,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_expense_paid_confirm_token_matches_admin_token_shape(self):
        admin = self.make_admin(site_id=2)
        payload = {"expense_id": 88}
        token = admin_router._build_confirm_token(
            admin,
            action="finance:expense:mark_paid:88",
            request_hash=expenses_router._stable_request_hash(payload),
            site_id=2,
        )

        expenses_router._require_confirm_token(
            admin=admin,
            site_id=2,
            action="finance:expense:mark_paid:88",
            payload=payload,
            confirm_token=token,
        )

        with self.assertRaises(HTTPException) as ctx:
            expenses_router._require_confirm_token(
                admin=admin,
                site_id=2,
                action="finance:expense:mark_paid:89",
                payload=payload,
                confirm_token=token,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_finance_withdraw_requires_confirm_token_and_uses_request_site(self):
        from schemas.finance import WithdrawRequest

        admin = self.make_admin(site_id=2)
        body = WithdrawRequest(amount=Decimal("12.30"), bank_account="bank-1", remark="提现")
        payload = body.model_dump(mode="json", exclude_none=True)
        token = admin_router._build_confirm_token(
            admin,
            action="finance:withdraw",
            request_hash=finance_router._stable_request_hash(payload),
            site_id=2,
        )
        request = SimpleNamespace(headers={"X-Site-Id": "2"})

        with patch.object(
            finance_router.finance_service,
            "withdraw",
            AsyncMock(return_value={
                "transaction_no": "WD202607090001",
                "amount": Decimal("12.30"),
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
            }),
        ) as withdraw:
            await finance_router.withdraw(
                body,
                request=request,
                db=SimpleNamespace(),
                admin=admin,
                x_confirm_token=token,
            )

        withdraw.assert_awaited_once()
        _, kwargs = withdraw.await_args
        self.assertEqual(kwargs["site_id"], 2)
        self.assertEqual(kwargs["operator_id"], 9)

        with self.assertRaises(HTTPException) as ctx:
            await finance_router.withdraw(
                body,
                request=request,
                db=SimpleNamespace(),
                admin=admin,
                x_confirm_token=None,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_finance_deposit_refund_requires_confirm_token_and_uses_request_site(self):
        from schemas.finance import DepositRefundRequest

        admin = self.make_admin(site_id=2)
        body = DepositRefundRequest(return_amount=Decimal("50.00"), remark="退押金")
        payload = {"deposit_id": 88, **body.model_dump(mode="json", exclude_none=True)}
        token = admin_router._build_confirm_token(
            admin,
            action="finance:deposit_refund",
            request_hash=finance_router._stable_request_hash(payload),
            site_id=2,
        )
        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        deposit = SimpleNamespace(
            id=88,
            order_id=18,
            order_item_id=28,
            deposit_amount=Decimal("100.00"),
            status="returned",
            return_amount=Decimal("50.00"),
            deduct_amount=Decimal("50.00"),
            damage_level=None,
            damage_photos=None,
            damage_remark=None,
            processed_by=9,
            processed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )

        with patch.object(
            finance_router.finance_service,
            "return_deposit",
            AsyncMock(return_value=deposit),
        ) as return_deposit:
            await finance_router.refund_deposit(
                88,
                body,
                request=request,
                db=SimpleNamespace(),
                admin=admin,
                x_confirm_token=token,
            )

        return_deposit.assert_awaited_once()
        _, kwargs = return_deposit.await_args
        self.assertEqual(kwargs["site_id"], 2)
        self.assertEqual(kwargs["operator_id"], 9)

        with self.assertRaises(HTTPException) as ctx:
            await finance_router.refund_deposit(
                88,
                body,
                request=request,
                db=SimpleNamespace(),
                admin=admin,
                x_confirm_token=None,
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
