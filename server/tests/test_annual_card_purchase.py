import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


class _FakeResult:
    def __init__(self, scalar_value=None):
        self._scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return self

    def first(self):
        values = self.all()
        return values[0] if values else None

    def all(self):
        if self._scalar_value is None:
            return []
        if isinstance(self._scalar_value, list):
            return list(self._scalar_value)
        return [self._scalar_value]


class _FakeDb:
    def __init__(self, scalar_values=None, flush_side_effect=None):
        self.added = []
        self.flushed = False
        self._scalar_values = list(scalar_values or [])
        self._flush_side_effect = flush_side_effect

    def add(self, obj):
        self.added.append(obj)

    def begin_nested(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def flush(self):
        if self._flush_side_effect is not None:
            raise self._flush_side_effect
        self.flushed = True

    async def execute(self, *args, **kwargs):
        value = self._scalar_values.pop(0) if self._scalar_values else None
        return _FakeResult(value)


class AnnualCardPurchaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_purchase_annual_card_creates_pending_membership_order(self):
        from models.order import Order
        from schemas.member import AnnualCardPurchaseRequest
        from services import member_service
        from utils.security import hash_sensitive, mask_id_card

        config = SimpleNamespace(
            id=11,
            site_id=1,
            card_name="西郊林场年卡",
            price=Decimal("399.00"),
            duration_days=365,
            refund_days=7,
            status="active",
            is_deleted=False,
        )
        user = SimpleNamespace(id=7, site_id=1)
        db = _FakeDb([config, user, None, []])
        body = AnnualCardPurchaseRequest(
            config_id=11,
            real_name="张三",
            id_card="110101199001011234",
            payment_method="wechat_pay",
        )

        order = await member_service.purchase_annual_card(
            db,
            user,
            body,
            site_id=1,
        )

        self.assertIsInstance(order, Order)
        self.assertEqual(order.user_id, 7)
        self.assertEqual(order.site_id, 1)
        self.assertEqual(order.order_type, "annual_card")
        self.assertEqual(order.status, "pending_payment")
        self.assertEqual(order.payment_status, "unpaid")
        self.assertEqual(order.total_amount, Decimal("399.00"))
        self.assertEqual(order.actual_amount, Decimal("399.00"))
        self.assertEqual(order.payment_method, "wechat_pay")
        self.assertEqual(order.biz_data["membership_card"]["config_id"], 11)
        self.assertEqual(order.biz_data["membership_card"]["card_kind"], "annual")
        self.assertEqual(order.biz_data["membership_card"]["real_name"], "张三")
        self.assertEqual(order.biz_data["membership_card"]["id_card_masked"], mask_id_card("110101199001011234"))
        self.assertEqual(order.biz_data["membership_card"]["id_card_hash"], hash_sensitive("110101199001011234"))
        self.assertNotIn("110101199001011234", str(order.biz_data))
        self.assertTrue(db.flushed)

    async def test_purchase_annual_card_rejects_existing_pending_order(self):
        from schemas.member import AnnualCardPurchaseRequest
        from services import member_service

        config = SimpleNamespace(
            id=11,
            site_id=1,
            card_name="西郊林场年卡",
            price=Decimal("399.00"),
            duration_days=365,
            refund_days=7,
            status="active",
            is_deleted=False,
        )
        pending_order = SimpleNamespace(id=88, order_no="YY202606270088")
        user = SimpleNamespace(id=7, site_id=1)
        db = _FakeDb([config, user, None, [pending_order]])
        body = AnnualCardPurchaseRequest(
            config_id=11,
            real_name="张三",
            id_card="110101199001011234",
            payment_method="wechat_pay",
        )

        with self.assertRaises(HTTPException) as cm:
            await member_service.purchase_annual_card(
                db,
                user,
                body,
                site_id=1,
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.detail["code"], 40920)
        self.assertIn("待支付", cm.exception.detail["message"])
        self.assertEqual(db.added, [])
        self.assertFalse(db.flushed)

    async def test_purchase_annual_card_handles_pending_order_unique_race(self):
        from schemas.member import AnnualCardPurchaseRequest
        from services import member_service

        config = SimpleNamespace(
            id=11,
            site_id=1,
            card_name="西郊林场年卡",
            price=Decimal("399.00"),
            duration_days=365,
            refund_days=7,
            status="active",
            is_deleted=False,
        )
        user = SimpleNamespace(id=7, site_id=1)
        db = _FakeDb(
            [config, user, None, []],
            flush_side_effect=IntegrityError(
                "insert annual order",
                {},
                Exception("duplicate key value violates unique constraint uq_order_annual_pending_active"),
            ),
        )
        body = AnnualCardPurchaseRequest(
            config_id=11,
            real_name="张三",
            id_card="110101199001011234",
            payment_method="wechat_pay",
        )

        with self.assertRaises(HTTPException) as cm:
            await member_service.purchase_annual_card(
                db,
                user,
                body,
                site_id=1,
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.detail["code"], 40920)
        self.assertIn("待支付", cm.exception.detail["message"])
        self.assertEqual(len(db.added), 1)

    async def test_mark_order_paid_activates_annual_card(self):
        from services import order_service

        order = SimpleNamespace(
            id=12,
            order_no="YY202606270001",
            user_id=7,
            site_id=1,
            order_type="annual_card",
            status="pending_payment",
            payment_status="unpaid",
            payment_method="wechat_pay",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            items=[],
        )

        with (
            patch.object(order_service.settlement_service, "record_payment_pending_income", AsyncMock()),
            patch.object(order_service.member_service, "activate_annual_card_for_paid_order", AsyncMock()) as activate_card,
            patch.object(order_service, "_generate_tickets", AsyncMock(return_value=[])) as generate_tickets,
        ):
            await order_service.mark_order_paid(
                _FakeDb(),
                order,
                payment_no="WX123",
                payment_method="wechat_pay",
            )

        activate_card.assert_awaited_once()
        self.assertIs(activate_card.await_args.args[1], order)
        generate_tickets.assert_not_awaited()
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")

    async def test_mark_order_paid_repairs_paid_annual_order_without_card(self):
        from services import order_service

        order = SimpleNamespace(
            id=12,
            order_no="YY202606270001",
            user_id=7,
            site_id=1,
            order_type="annual_card",
            status="paid",
            payment_status="paid",
            payment_method="wechat_pay",
            expire_at=None,
            items=[],
        )

        with patch.object(
            order_service.member_service,
            "activate_annual_card_for_paid_order",
            AsyncMock(),
        ) as activate_card:
            await order_service.mark_order_paid(
                _FakeDb(),
                order,
                payment_no="WX123",
                payment_method="wechat_pay",
            )

        activate_card.assert_awaited_once()
        self.assertIs(activate_card.await_args.args[1], order)

    async def test_activate_annual_card_for_paid_order_is_idempotent(self):
        from models.member import AnnualCard
        from services import member_service
        from utils.security import hash_sensitive

        config = SimpleNamespace(id=11, duration_days=365)
        existing_card = SimpleNamespace(id=99, order_id=12)
        order = SimpleNamespace(
            id=12,
            user_id=7,
            site_id=1,
            order_type="annual_card",
            biz_data={
                "membership_card": {
                    "config_id": 11,
                    "real_name": "张三",
                    "id_card_encrypted": "encrypted-id-card",
                    "id_card_hash": hash_sensitive("110101199001011234"),
                }
            },
        )

        existing_db = _FakeDb([SimpleNamespace(id=7, site_id=1), existing_card])
        self.assertIs(
            await member_service.activate_annual_card_for_paid_order(existing_db, order),
            existing_card,
        )
        self.assertEqual(existing_db.added, [])

        db = _FakeDb([SimpleNamespace(id=7, site_id=1), None, None, config])
        card = await member_service.activate_annual_card_for_paid_order(db, order)

        self.assertIsInstance(card, AnnualCard)
        self.assertEqual(card.user_id, 7)
        self.assertEqual(card.config_id, 11)
        self.assertEqual(card.order_id, 12)
        self.assertEqual(card.start_date, date.today())
        self.assertEqual(card.end_date, date.today() + timedelta(days=364))
        self.assertEqual(card.real_name, "张三")
        self.assertEqual(card.id_card_encrypted, "encrypted-id-card")
        self.assertEqual(card.id_card_hash, hash_sensitive("110101199001011234"))
        self.assertEqual(card.status, "active")
        self.assertEqual(card.site_id, 1)
        self.assertTrue(db.flushed)

    async def test_activate_annual_card_for_paid_order_rejects_other_active_card(self):
        from services import member_service
        from utils.security import hash_sensitive

        other_active_card = SimpleNamespace(id=99, order_id=77, duration_days=365)
        order = SimpleNamespace(
            id=12,
            user_id=7,
            site_id=1,
            order_type="annual_card",
            biz_data={
                "membership_card": {
                    "config_id": 11,
                    "real_name": "张三",
                    "id_card_encrypted": "encrypted-id-card",
                    "id_card_hash": hash_sensitive("110101199001011234"),
                }
            },
        )
        db = _FakeDb([SimpleNamespace(id=7, site_id=1), None, other_active_card])

        with self.assertRaises(HTTPException) as cm:
            await member_service.activate_annual_card_for_paid_order(db, order)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.detail["code"], 40920)
        self.assertIn("已存在有效年卡", cm.exception.detail["message"])
        self.assertEqual(db.added, [])
        self.assertFalse(db.flushed)

    async def test_activate_annual_card_for_paid_order_handles_order_unique_race(self):
        from services import member_service
        from utils.security import hash_sensitive

        config = SimpleNamespace(id=11, duration_days=365)
        order = SimpleNamespace(
            id=12,
            user_id=7,
            site_id=1,
            order_type="annual_card",
            biz_data={
                "membership_card": {
                    "config_id": 11,
                    "real_name": "张三",
                    "id_card_encrypted": "encrypted-id-card",
                    "id_card_hash": hash_sensitive("110101199001011234"),
                }
            },
        )
        concurrent_card = SimpleNamespace(id=99, order_id=12)
        db = _FakeDb(
            [SimpleNamespace(id=7, site_id=1), None, None, config, concurrent_card],
            flush_side_effect=IntegrityError(
                "insert annual card",
                {},
                Exception("duplicate key value violates unique constraint uq_ac_order"),
            ),
        )

        result = await member_service.activate_annual_card_for_paid_order(db, order)

        self.assertIs(result, concurrent_card)

    async def test_annual_card_refund_after_configured_window_is_rejected(self):
        from services import refund_service

        config = SimpleNamespace(id=11, refund_days=7)
        db = _FakeDb([None, config])
        order = SimpleNamespace(
            id=12,
            site_id=1,
            order_type="annual_card",
            status="paid",
            payment_status="paid",
            payment_time=datetime.now(timezone.utc) - timedelta(days=8, minutes=1),
            actual_amount=Decimal("399.00"),
            refunded_amount=Decimal("0.00"),
            refund_status="none",
            settlement_status="settled",
            biz_data={"membership_card": {"config_id": 11}},
            items=[],
            tickets=[],
        )

        with self.assertRaises(HTTPException) as cm:
            await refund_service.create_refund_record(
                db,
                order,
                refund_mode="full",
                order_action="cancel_order",
                refund_amount=Decimal("399.00"),
                release_inventory=False,
                reason="年卡退款",
                requested_by=7,
                requester_role="user",
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("年卡购买超过7天", cm.exception.detail["message"])

    async def test_refund_success_marks_annual_card_refunded_and_deducts_available(self):
        from services import refund_service

        account = SimpleNamespace(pending_amount=Decimal("0.00"), available_amount=Decimal("500.00"))
        card = SimpleNamespace(status="active")
        order = SimpleNamespace(
            id=12,
            site_id=1,
            order_type="annual_card",
            status="paid",
            payment_status="paid",
            actual_amount=Decimal("399.00"),
            refunded_amount=Decimal("0.00"),
            settlement_status="settled",
            items=[],
            tickets=[],
        )
        refund = SimpleNamespace(
            id=5,
            order_id=12,
            site_id=1,
            refund_amount=Decimal("399.00"),
            refund_mode="full",
            order_action="cancel_order",
            release_inventory=False,
            inventory_released=False,
            items=[],
            status="approved",
            wechat_refund_id=None,
            completed_at=None,
        )
        db = _FakeDb([card])

        with (
            patch.object(refund_service, "_find_existing_refund_tx", AsyncMock(return_value=None)),
            patch.object(refund_service, "_get_order_by_id", AsyncMock(return_value=order)),
            patch.object(refund_service, "_get_finance_account", AsyncMock(return_value=account)),
        ):
            tx = await refund_service.apply_refund_success(db, refund)

        self.assertEqual(account.available_amount, Decimal("101.00"))
        self.assertEqual(tx.account_type, "available")
        self.assertEqual(card.status, "refunded")
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.payment_status, "refunded")
        self.assertEqual(order.refund_status, "refunded")


if __name__ == "__main__":
    unittest.main()
