import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from routers import orders
from schemas.order import RefundRequest


class OrderRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_order_reloads_order_detail_before_serializing(self):
        db = object()
        user = SimpleNamespace(id=7)
        created_order = SimpleNamespace(id=12)
        order_detail = SimpleNamespace(id=12, items=[])
        body = SimpleNamespace(
            items=[SimpleNamespace(model_dump=lambda: {"product_id": 1})],
            disclaimer_signed=True,
            disclaimer_template_id=None,
            address_id=None,
            remark=None,
            payment_method="wechat_pay",
            times_card_id=None,
            source_qrcode_id=9,
            source_channel="poster",
            source_scanned_at="2026-06-18T14:00:00Z",
        )

        with (
            patch.object(orders.order_service, "create_order", AsyncMock(return_value=created_order)) as create_order,
            patch.object(orders.order_service, "get_order_detail", AsyncMock(return_value=order_detail)) as get_order_detail,
            patch.object(orders.OrderResponse, "model_validate", return_value={"id": 12}) as model_validate,
        ):
            await orders.create_order(body, db=db, user=user)

        create_order.assert_awaited_once_with(
            db,
            user,
            [{"product_id": 1}],
            disclaimer_signed=True,
            disclaimer_template_id=None,
            address_id=None,
            remark=None,
            payment_method="wechat_pay",
            times_card_id=None,
            source_qrcode_id=9,
            source_channel="poster",
            source_scanned_at="2026-06-18T14:00:00Z",
        )
        get_order_detail.assert_awaited_once_with(db, 12, user_id=7)
        model_validate.assert_called_once_with(order_detail)

    async def test_apply_refund_creates_refund_record_before_serializing(self):
        db = object()
        user = SimpleNamespace(id=7)
        order = SimpleNamespace(id=12, site_id=1, user_id=7, actual_amount=Decimal("88.00"), items=[])
        order_detail = SimpleNamespace(id=12, items=[])

        with (
            patch.object(orders.refund_service, "get_order_for_refund", AsyncMock(return_value=order)) as get_order_for_refund,
            patch.object(orders.refund_service, "create_refund_record", AsyncMock()) as create_refund_record,
            patch.object(orders.order_service, "get_order_detail", AsyncMock(return_value=order_detail)) as get_order_detail,
            patch.object(orders.OrderResponse, "model_validate", return_value={"id": 12}) as model_validate,
        ):
            await orders.apply_refund(
                12,
                body=RefundRequest(reason="用户申请退款"),
                db=db,
                user=user,
            )

        get_order_for_refund.assert_awaited_once_with(db, order_id=12, site_id=1)
        create_refund_record.assert_awaited_once_with(
            db,
            order,
            refund_mode="full",
            order_action="cancel_order",
            refund_amount=Decimal("88.00"),
            release_inventory=True,
            reason="用户申请退款",
            requested_by=7,
            requester_role="user",
            items=None,
        )
        get_order_detail.assert_awaited_once_with(db, 12, user_id=7)
        model_validate.assert_called_once_with(order_detail)

    async def test_apply_partial_refund_creates_item_refund_record_without_old_inventory_release(self):
        db = object()
        user = SimpleNamespace(id=7)
        order = SimpleNamespace(
            id=12,
            site_id=1,
            user_id=7,
            actual_amount=Decimal("100.00"),
            items=[
                SimpleNamespace(id=30, actual_price=Decimal("40.00"), quantity=2),
                SimpleNamespace(id=31, actual_price=Decimal("60.00"), quantity=1),
            ],
        )
        order_detail = SimpleNamespace(id=12, items=[])

        with (
            patch.object(orders.refund_service, "get_order_for_refund", AsyncMock(return_value=order)),
            patch.object(orders.refund_service, "create_refund_record", AsyncMock()) as create_refund_record,
            patch.object(orders.order_service, "get_order_detail", AsyncMock(return_value=order_detail)),
            patch.object(orders.order_service, "apply_refund", AsyncMock()) as old_apply_refund,
            patch.object(orders.OrderResponse, "model_validate", return_value={"id": 12}),
        ):
            await orders.apply_refund(
                12,
                body=RefundRequest(reason="退其中一项", order_item_ids=[30]),
                db=db,
                user=user,
            )

        old_apply_refund.assert_not_awaited()
        create_refund_record.assert_awaited_once_with(
            db,
            order,
            refund_mode="item",
            order_action="keep_order",
            refund_amount=Decimal("40.00"),
            release_inventory=True,
            reason="退其中一项",
            requested_by=7,
            requester_role="user",
            items=[{"order_item_id": 30, "refund_amount": Decimal("40.00"), "quantity": 2}],
        )


if __name__ == "__main__":
    unittest.main()
