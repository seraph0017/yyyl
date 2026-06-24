import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class FakeDb:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


class SettlementServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services import settlement_service

        self.service = settlement_service

    async def test_record_payment_pending_income_adds_to_pending_once(self):
        db = FakeDb()
        account = SimpleNamespace(pending_amount=Decimal("10.00"), total_income=Decimal("10.00"))
        order = SimpleNamespace(
            id=12,
            site_id=1,
            actual_amount=Decimal("99.00"),
            payment_method="wechat_pay",
            payment_no="WX123",
        )

        with (
            patch.object(self.service, "_find_existing_income_tx", AsyncMock(return_value=None)),
            patch.object(self.service, "_get_or_create_finance_account", AsyncMock(return_value=account)),
        ):
            tx = await self.service.record_payment_pending_income(db, order)

        self.assertEqual(account.pending_amount, Decimal("109.00"))
        self.assertEqual(account.total_income, Decimal("109.00"))
        self.assertEqual(tx.type, "income")
        self.assertEqual(tx.account_type, "pending")
        self.assertEqual(tx.order_id, 12)
        self.assertTrue(db.flushed)

    async def test_record_payment_pending_income_is_idempotent(self):
        db = FakeDb()
        existing = SimpleNamespace(id=99)
        order = SimpleNamespace(
            id=12,
            site_id=1,
            actual_amount=Decimal("99.00"),
            payment_method="wechat_pay",
            payment_no="WX123",
        )

        with patch.object(self.service, "_find_existing_income_tx", AsyncMock(return_value=existing)):
            tx = await self.service.record_payment_pending_income(db, order)

        self.assertIs(tx, existing)
        self.assertEqual(db.added, [])

    async def test_record_payment_pending_income_skips_non_cash_methods(self):
        db = FakeDb()
        order = SimpleNamespace(
            id=12,
            site_id=1,
            actual_amount=Decimal("99.00"),
            payment_method="times_card",
            payment_no="TC123",
        )

        tx = await self.service.record_payment_pending_income(db, order)

        self.assertIsNone(tx)
        self.assertEqual(db.added, [])

    async def test_settle_completed_order_moves_pending_to_available(self):
        db = FakeDb()
        account = SimpleNamespace(
            pending_amount=Decimal("120.00"),
            available_amount=Decimal("30.00"),
        )
        order = SimpleNamespace(
            id=21,
            site_id=2,
            status="completed",
            actual_amount=Decimal("100.00"),
            refunded_amount=Decimal("20.00"),
            settled_amount=Decimal("0.00"),
            settlement_status="unsettled",
        )

        with (
            patch.object(self.service, "_find_completed_settlement", AsyncMock(return_value=None)),
            patch.object(self.service, "_get_or_create_finance_account", AsyncMock(return_value=account)),
        ):
            settlement = await self.service.settle_completed_order(db, order, trigger_type="auto")

        self.assertEqual(account.pending_amount, Decimal("40.00"))
        self.assertEqual(account.available_amount, Decimal("110.00"))
        self.assertEqual(order.settled_amount, Decimal("80.00"))
        self.assertEqual(order.settlement_status, "settled")
        self.assertEqual(settlement.order_id, 21)
        self.assertEqual(settlement.site_id, 2)
        self.assertEqual(settlement.amount, Decimal("80.00"))
        self.assertEqual(settlement.status, "completed")
        self.assertEqual(settlement.trigger_type, "auto")
        tx = next(obj for obj in db.added if getattr(obj, "type", None) == "settlement")
        self.assertEqual(tx.account_type, "available")
        self.assertEqual(tx.from_account, "pending")
        self.assertEqual(tx.to_account, "available")
        self.assertTrue(db.flushed)

    async def test_settle_completed_order_is_idempotent(self):
        db = FakeDb()
        existing = SimpleNamespace(id=88, status="completed")
        order = SimpleNamespace(
            id=21,
            site_id=2,
            status="completed",
            actual_amount=Decimal("100.00"),
            refunded_amount=Decimal("0.00"),
            settled_amount=Decimal("100.00"),
            settlement_status="settled",
        )

        with patch.object(self.service, "_find_completed_settlement", AsyncMock(return_value=existing)):
            settlement = await self.service.settle_completed_order(db, order, trigger_type="auto")

        self.assertIs(settlement, existing)
        self.assertEqual(db.added, [])

    async def test_settle_completed_order_records_failure_when_pending_is_insufficient(self):
        db = FakeDb()
        account = SimpleNamespace(
            pending_amount=Decimal("30.00"),
            available_amount=Decimal("0.00"),
        )
        order = SimpleNamespace(
            id=21,
            site_id=2,
            status="completed",
            actual_amount=Decimal("80.00"),
            refunded_amount=Decimal("0.00"),
            settled_amount=Decimal("0.00"),
            settlement_status="unsettled",
        )

        with (
            patch.object(self.service, "_find_completed_settlement", AsyncMock(return_value=None)),
            patch.object(self.service, "_get_or_create_finance_account", AsyncMock(return_value=account)),
        ):
            settlement = await self.service.settle_completed_order(db, order, trigger_type="auto")

        self.assertEqual(account.pending_amount, Decimal("30.00"))
        self.assertEqual(account.available_amount, Decimal("0.00"))
        self.assertEqual(order.settled_amount, Decimal("0.00"))
        self.assertEqual(order.settlement_status, "failed")
        self.assertEqual(settlement.status, "failed")
        self.assertIn("待结算余额不足", settlement.error_message)
        self.assertFalse(any(getattr(obj, "type", None) == "settlement" for obj in db.added))
        self.assertTrue(db.flushed)


if __name__ == "__main__":
    unittest.main()
