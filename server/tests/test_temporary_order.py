import json
import inspect
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError


class TemporaryOrderContractTest(unittest.TestCase):
    def test_temporary_order_session_model_and_migration_exist(self):
        import models  # noqa: F401
        from models.base import Base
        from models.order import OrderType, TemporaryOrderSession

        self.assertIn("temporary_order_session", Base.metadata.tables)
        self.assertEqual(OrderType.TEMPORARY.value, "temporary")
        columns = set(TemporaryOrderSession.__table__.columns.keys())
        self.assertTrue(
            {
                "site_id",
                "session_no",
                "token_hash",
                "status",
                "payment_flow",
                "mode",
                "product_id",
                "sku_id",
                "quantity",
                "booking_date",
                "time_slot",
                "item_name",
                "amount",
                "remark",
                "created_by_id",
                "created_by_source",
                "order_id",
                "expire_at",
                "audit_data",
            }.issubset(columns)
        )

        migration = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("alembic", "versions", "1a2b3c4d5e6f_v1_8_add_temporary_order_session.py")
        )
        self.assertTrue(migration.exists())
        source = migration.read_text(encoding="utf-8")
        self.assertIn("temporary_order_session", source)
        self.assertIn("idx_temp_order_session_site_status", source)
        self.assertIn("uq_temp_order_session_no", source)

    def test_temporary_order_schema_enforces_custom_amount_audit_fields(self):
        from schemas.order import TemporaryOrderCreateRequest

        body = TemporaryOrderCreateRequest(
            item_name="现场补差价",
            amount=Decimal("18.80"),
            remark="客户现场加购柴火",
        )
        self.assertEqual(body.mode, "custom_amount")
        self.assertEqual(body.payment_flow, "customer_scan_qr")

        with self.assertRaises(ValidationError):
            TemporaryOrderCreateRequest(item_name="现场补差价", amount=Decimal("18.80"))

    def test_temporary_order_schema_enforces_payment_code_auth_code(self):
        from schemas.order import TemporaryOrderCreateRequest

        with self.assertRaises(ValidationError):
            TemporaryOrderCreateRequest(
                payment_flow="merchant_scan_code",
                item_name="现场收款",
                amount=Decimal("20.00"),
                remark="付款码测试",
            )

        body = TemporaryOrderCreateRequest(
            payment_flow="merchant_scan_code",
            item_name="现场收款",
            amount=Decimal("20.00"),
            remark="付款码测试",
            auth_code="134567890123456789",
        )
        self.assertEqual(body.auth_code, "134567890123456789")


class TemporaryOrderServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_custom_temporary_session_returns_token_and_15_minute_expiry(self):
        from schemas.order import TemporaryOrderCreateRequest
        from services import order_service

        db = SimpleNamespace(add=lambda obj: setattr(db, "added", obj), flush=AsyncMock())
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        body = TemporaryOrderCreateRequest(
            item_name="现场补差价",
            amount=Decimal("18.80"),
            remark="客户现场加购柴火",
        )

        with (
            patch.object(order_service, "_now", return_value=now),
            patch.object(order_service, "_generate_temporary_order_token", return_value="plain-token"),
            patch.object(order_service, "_generate_temporary_session_no", return_value="TO202606270001"),
            patch.object(order_service.qrcode_service, "create_temporary_order_qrcode_image", AsyncMock(return_value="/images/qrcodes/temporary/2/plain-token.png")),
        ):
            session, token = await order_service.create_temporary_order_session(
                db,
                site_id=2,
                body=body,
                operator_id=9,
                operator_source="admin",
            )

        self.assertEqual(token, "plain-token")
        self.assertEqual(session.session_no, "TO202606270001")
        self.assertEqual(session.token_hash, order_service.hash_temporary_order_token("plain-token"))
        self.assertEqual(session.site_id, 2)
        self.assertEqual(session.status, "draft")
        self.assertEqual(session.mode, "custom_amount")
        self.assertEqual(session.item_name, "现场补差价")
        self.assertEqual(session.amount, Decimal("18.80"))
        self.assertEqual(session.remark, "客户现场加购柴火")
        self.assertEqual(session.expire_at, now + timedelta(minutes=15))
        self.assertEqual(session.audit_data["created_by_source"], "admin")
        self.assertEqual(session.audit_data["qrcode_image_url"], "/images/qrcodes/temporary/2/plain-token.png")
        db.flush.assert_awaited_once()

    def test_temporary_session_response_exposes_real_qrcode_image_url(self):
        from models.order import TemporaryOrderSession
        from services import order_service

        session = TemporaryOrderSession(
            id=12,
            site_id=1,
            session_no="TO202606270001",
            token_hash="hash",
            status="draft",
            payment_flow="customer_scan_qr",
            mode="custom_amount",
            quantity=1,
            item_name="现场补差价",
            amount=Decimal("18.80"),
            remark="客户现场加购柴火",
            created_by_id=9,
            created_by_source="admin",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            audit_data={"qrcode_image_url": "/images/qrcodes/temporary/1/token.png"},
        )

        payload = order_service.build_temporary_session_response_payload(session, token="plain-token")

        self.assertEqual(payload["qrcode_image_url"], "/images/qrcodes/temporary/1/token.png")
        self.assertEqual(payload["miniapp_path"], "/pages/order-confirm/index?temporary_token=plain-token")

    async def test_claim_custom_temporary_session_creates_formal_order_once(self):
        from models.order import TemporaryOrderSession
        from models.user import User
        from services import order_service

        user = User(id=7, openid="openid-test", site_id=1)
        session = TemporaryOrderSession(
            id=12,
            site_id=1,
            session_no="TO202606270001",
            token_hash=order_service.hash_temporary_order_token("plain-token"),
            status="draft",
            payment_flow="customer_scan_qr",
            mode="custom_amount",
            item_name="现场补差价",
            amount=Decimal("18.80"),
            remark="客户现场加购柴火",
            created_by_id=9,
            created_by_source="admin",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            audit_data={},
        )
        db = SimpleNamespace(add=lambda obj: setattr(db, "added", obj), flush=AsyncMock())

        with patch.object(order_service, "_get_temporary_session_by_token", AsyncMock(return_value=session)):
            order = await order_service.claim_temporary_order_session(
                db,
                site_id=1,
                token="plain-token",
                user=user,
            )

        self.assertEqual(order.user_id, 7)
        self.assertEqual(order.order_type, "temporary")
        self.assertEqual(order.actual_amount, Decimal("18.80"))
        self.assertEqual(order.expire_at.replace(microsecond=0), session.expire_at.replace(microsecond=0))
        self.assertEqual(order.biz_data["temporary_order"]["session_no"], "TO202606270001")
        self.assertTrue(order.biz_data["temporary_order"]["custom_amount"])
        self.assertEqual(session.status, "pending_payment")
        self.assertIs(session.order_id, order.id)
        self.assertEqual(session.audit_data["claimed_by_user_id"], 7)
        db.flush.assert_awaited()

    async def test_payment_code_uses_wechat_codepay_and_does_not_mark_userpaying_as_paid(self):
        from models.order import TemporaryOrderSession
        from services import order_service

        session = TemporaryOrderSession(
            id=12,
            site_id=1,
            session_no="TO202606270001",
            token_hash=order_service.hash_temporary_order_token("plain-token"),
            status="draft",
            payment_flow="merchant_scan_code",
            mode="custom_amount",
            item_name="现场收款",
            amount=Decimal("20.00"),
            remark="客户付款码",
            created_by_id=9,
            created_by_source="admin",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            audit_data={},
        )
        db = SimpleNamespace(add=lambda obj: setattr(db, "added", obj), flush=AsyncMock())

        with (
            patch.object(order_service, "_get_or_create_onsite_guest_user", AsyncMock(return_value=SimpleNamespace(id=88, openid="onsite:1", site_id=1))),
            patch.object(order_service.wechat_pay_service, "create_codepay_transaction", AsyncMock(return_value={"trade_state": "USERPAYING"})) as codepay,
            patch.object(order_service, "mark_order_paid", AsyncMock()) as mark_paid,
        ):
            order, result = await order_service.charge_temporary_order_by_auth_code(
                db,
                site_id=1,
                session=session,
                auth_code="134567890123456789",
                device_id="staff-phone-1",
            )

        self.assertEqual(order.user_id, 88)
        self.assertEqual(order.order_type, "temporary")
        codepay.assert_awaited_once()
        mark_paid.assert_not_awaited()
        self.assertEqual(result["trade_state"], "USERPAYING")
        self.assertTrue(result["requires_query"])
        self.assertEqual(session.status, "pending_payment")
        self.assertEqual(session.audit_data["auth_code_masked"], "134567******6789")

    def test_temporary_session_lookup_uses_row_lock_for_claim_idempotency(self):
        from services import order_service

        source = inspect.getsource(order_service._get_temporary_session_by_token)
        self.assertIn("with_for_update", source)

    async def test_payment_code_success_reloads_order_items_before_marking_paid(self):
        from models.order import TemporaryOrderSession
        from services import order_service

        session = TemporaryOrderSession(
            id=12,
            site_id=1,
            session_no="TO202606270001",
            token_hash=order_service.hash_temporary_order_token("plain-token"),
            status="draft",
            payment_flow="merchant_scan_code",
            mode="product",
            product_id=5,
            quantity=1,
            item_name=None,
            amount=None,
            remark="客户付款码",
            created_by_id=9,
            created_by_source="admin",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            audit_data={},
        )
        db = SimpleNamespace(flush=AsyncMock())
        created_order = SimpleNamespace(id=99, order_no="YY202606270001", actual_amount=Decimal("20.00"), user_id=88)
        reloaded_order = SimpleNamespace(id=99, order_no="YY202606270001", actual_amount=Decimal("20.00"), user_id=88, items=[SimpleNamespace(id=1)])

        with (
            patch.object(order_service, "_get_or_create_onsite_guest_user", AsyncMock(return_value=SimpleNamespace(id=88, site_id=1))),
            patch.object(order_service, "_create_order_from_temporary_session", AsyncMock(return_value=created_order)),
            patch.object(order_service, "get_order_detail", AsyncMock(return_value=reloaded_order)) as get_detail,
            patch.object(order_service.wechat_pay_service, "create_codepay_transaction", AsyncMock(return_value={"trade_state": "SUCCESS", "transaction_id": "4200001"})),
            patch.object(order_service, "mark_order_paid", AsyncMock()) as mark_paid,
        ):
            await order_service.charge_temporary_order_by_auth_code(
                db,
                site_id=1,
                session=session,
                auth_code="134567890123456789",
            )

        get_detail.assert_awaited_once_with(db, 99, user_id=88)
        mark_paid.assert_awaited_once_with(
            db,
            reloaded_order,
            payment_no="4200001",
            payment_method="wechat_pay",
        )
        self.assertEqual(session.status, "paid")

    async def test_query_temporary_codepay_success_marks_order_paid(self):
        from models.order import Order, TemporaryOrderSession
        from services import order_service

        session = TemporaryOrderSession(
            id=8,
            site_id=2,
            session_no="TO202606270008",
            token_hash=order_service.hash_temporary_order_token("plain-token"),
            status="pending_payment",
            payment_flow="merchant_scan_code",
            mode="custom_amount",
            quantity=1,
            amount=Decimal("12.30"),
            order_id=91,
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            audit_data={},
        )
        order = Order(
            id=91,
            site_id=2,
            order_no="ORD202606270091",
            user_id=5,
            total_amount=Decimal("12.30"),
            actual_amount=Decimal("12.30"),
            status="pending_payment",
            payment_status="unpaid",
            order_type="temporary",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        class FakeResult:
            def scalar_one_or_none(self):
                return session

        db = AsyncMock()
        db.execute.return_value = FakeResult()

        with (
            patch.object(order_service, "get_order_detail", AsyncMock(return_value=order)) as get_order,
            patch.object(order_service.wechat_pay_service, "query_codepay_transaction", AsyncMock(return_value={
                "trade_state": "SUCCESS",
                "transaction_id": "4200000091",
            })) as query_pay,
            patch.object(order_service, "mark_order_paid", AsyncMock(return_value=order)) as mark_paid,
        ):
            refreshed_session, refreshed_order, pay_result = await order_service.query_temporary_codepay_result(
                db,
                site_id=2,
                session_id=8,
                operator_id=3,
                operator_source="staff",
            )

        self.assertIs(refreshed_session, session)
        self.assertIs(refreshed_order, order)
        self.assertEqual(pay_result["trade_state"], "SUCCESS")
        self.assertEqual(pay_result["transaction_id"], "4200000091")
        self.assertEqual(session.status, "paid")
        self.assertEqual(session.audit_data["wechat_trade_state"], "SUCCESS")
        self.assertEqual(session.audit_data["wechat_transaction_id"], "4200000091")
        self.assertEqual(session.audit_data["last_query_by"], {"id": 3, "source": "staff"})
        get_order.assert_awaited_once_with(db, 91)
        query_pay.assert_awaited_once_with(order, site_id=2)
        mark_paid.assert_awaited_once_with(
            db,
            order,
            payment_no="4200000091",
            payment_method="wechat_pay",
            allow_expired=True,
        )


class TemporaryOrderRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_admin_create_temporary_order_session_calls_service_with_site_and_operator(self):
        from routers import orders
        from schemas.order import TemporaryOrderCreateRequest

        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        admin = SimpleNamespace(id=9, site_id=2, role=SimpleNamespace(role_code="admin"))
        session = SimpleNamespace(id=12, order_id=None)

        with (
            patch.object(orders.order_service, "create_temporary_order_session", AsyncMock(return_value=(session, "plain-token"))) as create_session,
            patch.object(
                orders.order_service,
                "build_temporary_session_response_payload",
                return_value={
                    "id": 12,
                    "session_no": "TO202606270001",
                    "token": "plain-token",
                    "status": "draft",
                    "payment_flow": "customer_scan_qr",
                    "mode": "custom_amount",
                    "quantity": 1,
                    "expire_at": datetime.now(timezone.utc) + timedelta(minutes=15),
                },
            ),
            patch.object(orders.TemporaryOrderSessionResponse, "model_validate", return_value={"id": 12}) as model_validate,
        ):
            await orders.admin_create_temporary_order(
                TemporaryOrderCreateRequest(
                    item_name="现场补差价",
                    amount=Decimal("18.80"),
                    remark="客户现场加购柴火",
                ),
                request=request,
                db=object(),
                admin=admin,
            )

        create_session.assert_awaited_once()
        _, kwargs = create_session.call_args
        self.assertEqual(kwargs["site_id"], 2)
        self.assertEqual(kwargs["operator_id"], 9)
        self.assertEqual(kwargs["operator_source"], "admin")
        model_validate.assert_called_once()

    async def test_admin_create_temporary_order_rejects_cross_site_non_super_admin(self):
        from routers import orders
        from schemas.order import TemporaryOrderCreateRequest

        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        admin = SimpleNamespace(id=9, site_id=1, role=SimpleNamespace(role_code="admin"))

        with self.assertRaises(HTTPException) as ctx:
            await orders.admin_create_temporary_order(
                TemporaryOrderCreateRequest(
                    item_name="现场补差价",
                    amount=Decimal("18.80"),
                    remark="跨营地测试",
                ),
                request=request,
                db=object(),
                admin=admin,
            )

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_admin_query_temporary_codepay_enforces_site_and_returns_codepay_response(self):
        from models.order import Order, TemporaryOrderSession
        from routers import orders

        admin = SimpleNamespace(id=4, site_id=2, role=SimpleNamespace(role_code="admin"))
        request = SimpleNamespace(headers={"X-Site-Id": "2"})
        session = TemporaryOrderSession(
            id=8,
            site_id=2,
            session_no="TO202606270008",
            token_hash="hash",
            status="paid",
            payment_flow="merchant_scan_code",
            mode="custom_amount",
            quantity=1,
            amount=Decimal("12.30"),
            order_id=91,
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        order = Order(
            id=91,
            site_id=2,
            order_no="ORD202606270091",
            user_id=5,
            total_amount=Decimal("12.30"),
            discount_amount=Decimal("0.00"),
            actual_amount=Decimal("12.30"),
            deposit_amount=Decimal("0.00"),
            status="paid",
            payment_status="paid",
            payment_method="wechat_pay",
            order_type="temporary",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(
                orders.order_service,
                "query_temporary_codepay_result",
                AsyncMock(return_value=(session, order, {"trade_state": "SUCCESS", "transaction_id": "4200000091"})),
            ) as query_result,
            patch.object(orders.order_service, "get_order_detail", AsyncMock(return_value=order)),
            patch.object(orders.order_service, "build_temporary_session_response_payload", return_value={
                "id": 8,
                "session_no": "TO202606270008",
                "status": "paid",
                "payment_flow": "merchant_scan_code",
                "mode": "custom_amount",
                "quantity": 1,
                "amount": Decimal("12.30"),
                "order_id": 91,
                "expire_at": session.expire_at,
            }),
        ):
            response = await orders.admin_query_temporary_codepay(
                8,
                request=request,
                db=AsyncMock(),
                admin=admin,
            )

        query_result.assert_awaited_once()
        _, kwargs = query_result.await_args
        self.assertEqual(kwargs["site_id"], 2)
        self.assertEqual(kwargs["session_id"], 8)
        self.assertEqual(kwargs["operator_id"], 4)
        self.assertEqual(kwargs["operator_source"], "admin")
        self.assertEqual(response.data.trade_state, "SUCCESS")
        self.assertEqual(response.data.transaction_id, "4200000091")
        self.assertFalse(response.data.requires_query)

    async def test_staff_query_temporary_codepay_uses_staff_site_and_source(self):
        from models.order import Order, TemporaryOrderSession
        from routers import orders

        staff = SimpleNamespace(id=9, site_id=1, source="staff")
        session = TemporaryOrderSession(
            id=3,
            site_id=1,
            session_no="TO202606270003",
            token_hash="hash",
            status="pending_payment",
            payment_flow="merchant_scan_code",
            mode="custom_amount",
            quantity=1,
            amount=Decimal("8.80"),
            order_id=77,
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        order = Order(
            id=77,
            site_id=1,
            order_no="ORD202606270077",
            user_id=5,
            total_amount=Decimal("8.80"),
            discount_amount=Decimal("0.00"),
            actual_amount=Decimal("8.80"),
            deposit_amount=Decimal("0.00"),
            status="pending_payment",
            payment_status="unpaid",
            payment_method="wechat_pay",
            order_type="temporary",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with (
            patch.object(
                orders.order_service,
                "query_temporary_codepay_result",
                AsyncMock(return_value=(session, order, {"trade_state": "USERPAYING", "requires_query": True})),
            ) as query_result,
            patch.object(orders.order_service, "get_order_detail", AsyncMock(return_value=order)),
            patch.object(orders.order_service, "build_temporary_session_response_payload", return_value={
                "id": 3,
                "session_no": "TO202606270003",
                "status": "pending_payment",
                "payment_flow": "merchant_scan_code",
                "mode": "custom_amount",
                "quantity": 1,
                "amount": Decimal("8.80"),
                "order_id": 77,
                "expire_at": session.expire_at,
            }),
        ):
            response = await orders.staff_query_temporary_codepay(
                3,
                db=AsyncMock(),
                staff=staff,
            )

        _, kwargs = query_result.await_args
        self.assertEqual(kwargs["site_id"], 1)
        self.assertEqual(kwargs["session_id"], 3)
        self.assertEqual(kwargs["operator_id"], 9)
        self.assertEqual(kwargs["operator_source"], "staff")
        self.assertTrue(response.data.requires_query)


class WechatPayCodepayTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_codepay_transaction_posts_server_side_amount_and_auth_code(self):
        from services import wechat_pay_service

        config = wechat_pay_service.WechatPayConfig(
            app_id="wx-test",
            mch_id="1619737660",
            mch_serial_no="SERIAL123",
            api_v3_key="0123456789abcdeffedcba9876543210",
            private_key_pem="pem",
            platform_public_key_pem="platform",
            platform_public_key_id="PUB_KEY_ID_TEST",
            notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/notify",
            refund_notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/refund-notify",
        )
        order = SimpleNamespace(order_no="YY202606270001", actual_amount=Decimal("20.00"))

        with (
            patch.object(wechat_pay_service, "get_wechat_pay_config", return_value=config),
            patch.object(
                wechat_pay_service,
                "_wechat_post",
                AsyncMock(return_value={"trade_state": "SUCCESS", "transaction_id": "4200001"}),
            ) as post,
        ):
            result = await wechat_pay_service.create_codepay_transaction(
                order,
                auth_code="134567890123456789",
                site_id=1,
                device_id="staff-phone-1",
            )

        post.assert_awaited_once()
        config_arg, path, payload = post.await_args.args
        self.assertEqual(path, "/v3/pay/transactions/codepay")
        self.assertEqual(payload["appid"], "wx-test")
        self.assertEqual(payload["mchid"], "1619737660")
        self.assertEqual(payload["out_trade_no"], "YY202606270001")
        self.assertEqual(payload["auth_code"], "134567890123456789")
        self.assertEqual(payload["amount"]["total"], 2000)
        self.assertEqual(payload["scene_info"]["device_id"], "staff-phone-1")
        self.assertEqual(config_arg, config)
        self.assertEqual(result["trade_state"], "SUCCESS")

    async def test_query_codepay_transaction_uses_out_trade_no_and_mchid(self):
        from services import wechat_pay_service

        config = wechat_pay_service.WechatPayConfig(
            app_id="wx-test",
            mch_id="1619737660",
            mch_serial_no="SERIAL123",
            api_v3_key="0123456789abcdeffedcba9876543210",
            private_key_pem="pem",
            platform_public_key_pem="platform",
            platform_public_key_id="PUB_KEY_ID_TEST",
            notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/notify",
            refund_notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/refund-notify",
        )
        order = SimpleNamespace(order_no="YY202606270001")

        with (
            patch.object(wechat_pay_service, "get_wechat_pay_config", return_value=config),
            patch.object(
                wechat_pay_service,
                "_wechat_get",
                AsyncMock(return_value={"trade_state": "SUCCESS", "transaction_id": "4200001"}),
            ) as get_call,
        ):
            result = await wechat_pay_service.query_codepay_transaction(order, site_id=1)

        get_call.assert_awaited_once()
        _, path = get_call.await_args.args
        self.assertEqual(path, "/v3/pay/transactions/out-trade-no/YY202606270001?mchid=1619737660")
        self.assertEqual(result["trade_state"], "SUCCESS")


class TemporaryOrderQrcodeTest(unittest.IsolatedAsyncioTestCase):
    async def test_temporary_order_qrcode_uses_order_confirm_page_and_token_scene(self):
        from services import qrcode_service

        response = SimpleNamespace(
            headers={"content-type": "image/png"},
            content=b"png-bytes",
        )
        async_client = AsyncMock()
        async_client.__aenter__.return_value.post.return_value = response

        with (
            patch.object(qrcode_service, "_get_wechat_access_token", AsyncMock(return_value="ACCESS")),
            patch.object(qrcode_service.httpx, "AsyncClient", return_value=async_client),
            patch.object(qrcode_service.Path, "write_bytes", return_value=None),
        ):
            image_url = await qrcode_service.create_temporary_order_qrcode_image(
                site_id=1,
                token="plain-token",
            )

        post_call = async_client.__aenter__.return_value.post.call_args
        self.assertIn("/wxa/getwxacodeunlimit?access_token=ACCESS", post_call.args[0])
        self.assertEqual(post_call.kwargs["json"]["page"], "pages/order-confirm/index")
        self.assertEqual(post_call.kwargs["json"]["scene"], "plain-token")
        self.assertTrue(image_url.startswith("/images/qrcodes/temporary/1/"))


if __name__ == "__main__":
    unittest.main()
