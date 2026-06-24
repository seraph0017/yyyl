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


class RefundServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services import refund_service

        self.service = refund_service

    async def test_create_refund_record_full_keep_order_keeps_order_status(self):
        db = FakeDb()
        order = SimpleNamespace(
            id=10,
            site_id=2,
            status="paid",
            payment_status="paid",
            actual_amount=Decimal("120.00"),
            refunded_amount=Decimal("0.00"),
            refund_status="none",
            items=[
                SimpleNamespace(
                    id=101,
                    actual_price=Decimal("120.00"),
                    quantity=1,
                    refund_status="none",
                )
            ],
            tickets=[],
        )

        refund = await self.service.create_refund_record(
            db,
            order,
            refund_mode="full",
            order_action="keep_order",
            refund_amount=Decimal("120.00"),
            release_inventory=False,
            reason="服务补偿",
            requested_by=7,
            requester_role="super_admin",
        )

        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(order.refund_status, "pending")
        self.assertEqual(order.refunded_amount, Decimal("120.00"))
        self.assertEqual(order.items[0].refund_status, "refunded")
        self.assertEqual(refund.site_id, 2)
        self.assertEqual(refund.order_id, 10)
        self.assertEqual(refund.refund_mode, "full")
        self.assertEqual(refund.order_action, "keep_order")
        self.assertEqual(refund.status, "pending")
        self.assertEqual(refund.system_amount, Decimal("120.00"))
        self.assertFalse(refund.release_inventory)
        self.assertTrue(db.flushed)

    async def test_create_refund_record_partial_uses_item_amounts(self):
        db = FakeDb()
        order = SimpleNamespace(
            id=10,
            site_id=2,
            status="paid",
            payment_status="paid",
            actual_amount=Decimal("120.00"),
            refunded_amount=Decimal("0.00"),
            refund_status="none",
            items=[
                SimpleNamespace(id=101, actual_price=Decimal("70.00"), quantity=1, refund_status="none"),
                SimpleNamespace(id=102, actual_price=Decimal("50.00"), quantity=1, refund_status="none"),
            ],
            tickets=[],
        )

        refund = await self.service.create_refund_record(
            db,
            order,
            refund_mode="item",
            order_action="keep_order",
            refund_amount=Decimal("50.00"),
            release_inventory=False,
            reason="单项退款",
            requested_by=7,
            items=[{"order_item_id": 102, "refund_amount": Decimal("50.00"), "quantity": 1}],
        )

        refund_items = [obj for obj in db.added if obj.__class__.__name__ == "RefundRecordItem"]
        self.assertEqual(refund.system_amount, Decimal("50.00"))
        self.assertEqual(len(refund_items), 1)
        self.assertEqual(refund_items[0].order_item_id, 102)
        self.assertEqual(order.items[0].refund_status, "none")
        self.assertEqual(order.items[1].refund_status, "refunded")

    async def test_cancel_order_refund_releases_inventory_and_voids_tickets(self):
        db = FakeDb()
        order_item = SimpleNamespace(
            id=101,
            product_id=5,
            sku_id=None,
            time_slot=None,
            date="2026-07-01",
            actual_price=Decimal("120.00"),
            quantity=2,
            refund_status="none",
        )
        ticket = SimpleNamespace(order_item_id=101, verify_status="pending")
        order = SimpleNamespace(
            id=10,
            site_id=2,
            status="paid",
            payment_status="paid",
            actual_amount=Decimal("120.00"),
            refunded_amount=Decimal("0.00"),
            refund_status="none",
            items=[order_item],
            tickets=[ticket],
        )

        with patch.object(self.service.order_service, "_refund_inventory", AsyncMock()) as refund_inventory:
            await self.service.create_refund_record(
                db,
                order,
                refund_mode="full",
                order_action="cancel_order",
                refund_amount=Decimal("120.00"),
                release_inventory=True,
                reason="取消订单",
                requested_by=7,
            )

        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.payment_status, "refunded")
        self.assertEqual(order.refund_status, "pending")
        self.assertEqual(ticket.verify_status, "refunded")
        refund_inventory.assert_awaited_once_with(
            db,
            5,
            "2026-07-01",
            2,
            10,
            None,
            None,
        )

    async def test_apply_completed_refund_deducts_pending_for_unsettled_order(self):
        db = FakeDb()
        account = SimpleNamespace(pending_amount=Decimal("200.00"), available_amount=Decimal("50.00"))
        order = SimpleNamespace(id=10, site_id=2, settlement_status="unsettled", refund_status="pending")
        refund = SimpleNamespace(
            id=5,
            order_id=10,
            site_id=2,
            refund_amount=Decimal("80.00"),
            status="approved",
            wechat_refund_id=None,
            completed_at=None,
        )

        with (
            patch.object(self.service, "_get_order_by_id", AsyncMock(return_value=order)),
            patch.object(self.service, "_get_finance_account", AsyncMock(return_value=account)),
            patch.object(self.service, "_find_existing_refund_tx", AsyncMock(return_value=None)),
        ):
            tx = await self.service.apply_refund_success(
                db,
                refund,
                wechat_refund_id="wx-refund-1",
            )

        self.assertEqual(account.pending_amount, Decimal("120.00"))
        self.assertEqual(account.available_amount, Decimal("50.00"))
        self.assertEqual(refund.status, "completed")
        self.assertEqual(order.refund_status, "refunded")
        self.assertEqual(refund.wechat_refund_id, "wx-refund-1")
        self.assertEqual(tx.type, "refund")
        self.assertEqual(tx.account_type, "pending")
        self.assertEqual(tx.refund_record_id, 5)

    async def test_apply_completed_refund_deducts_available_for_settled_order(self):
        db = FakeDb()
        account = SimpleNamespace(pending_amount=Decimal("20.00"), available_amount=Decimal("150.00"))
        order = SimpleNamespace(id=10, site_id=2, settlement_status="settled", refund_status="pending")
        refund = SimpleNamespace(
            id=5,
            order_id=10,
            site_id=2,
            refund_amount=Decimal("80.00"),
            status="approved",
            wechat_refund_id=None,
            completed_at=None,
        )

        with (
            patch.object(self.service, "_get_order_by_id", AsyncMock(return_value=order)),
            patch.object(self.service, "_get_finance_account", AsyncMock(return_value=account)),
            patch.object(self.service, "_find_existing_refund_tx", AsyncMock(return_value=None)),
        ):
            tx = await self.service.apply_refund_success(db, refund)

        self.assertEqual(account.pending_amount, Decimal("20.00"))
        self.assertEqual(account.available_amount, Decimal("70.00"))
        self.assertEqual(tx.account_type, "available")

    async def test_apply_completed_refund_fails_when_available_is_insufficient(self):
        from fastapi import HTTPException

        db = FakeDb()
        account = SimpleNamespace(pending_amount=Decimal("20.00"), available_amount=Decimal("30.00"))
        order = SimpleNamespace(id=10, site_id=2, settlement_status="settled", refund_status="pending")
        refund = SimpleNamespace(
            id=5,
            order_id=10,
            site_id=2,
            refund_amount=Decimal("80.00"),
            status="approved",
            wechat_refund_id=None,
            completed_at=None,
        )

        with (
            patch.object(self.service, "_get_order_by_id", AsyncMock(return_value=order)),
            patch.object(self.service, "_get_finance_account", AsyncMock(return_value=account)),
            patch.object(self.service, "_find_existing_refund_tx", AsyncMock(return_value=None)),
        ):
            with self.assertRaises(HTTPException):
                await self.service.apply_refund_success(db, refund)

        self.assertEqual(account.available_amount, Decimal("30.00"))
        self.assertEqual(order.refund_status, "rejected")
        self.assertEqual(refund.status, "failed")

    async def test_full_keep_order_requires_super_admin(self):
        from fastapi import HTTPException

        db = FakeDb()
        order = SimpleNamespace(
            id=10,
            site_id=2,
            status="paid",
            payment_status="paid",
            actual_amount=Decimal("120.00"),
            refunded_amount=Decimal("0.00"),
            refund_status="none",
            items=[],
            tickets=[],
        )

        with self.assertRaises(HTTPException):
            await self.service.create_refund_record(
                db,
                order,
                refund_mode="full",
                order_action="keep_order",
                refund_amount=Decimal("120.00"),
                release_inventory=False,
                reason="高风险退款",
                requested_by=7,
                requester_role="admin",
            )


if __name__ == "__main__":
    unittest.main()
