import unittest
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

    async def test_apply_refund_reloads_order_detail_before_serializing(self):
        db = object()
        user = SimpleNamespace(id=7)
        stale_order = SimpleNamespace(id=12)
        order_detail = SimpleNamespace(id=12, items=[])

        with (
            patch.object(orders.order_service, "apply_refund", AsyncMock(return_value=stale_order)) as apply_refund,
            patch.object(orders.order_service, "get_order_detail", AsyncMock(return_value=order_detail)) as get_order_detail,
            patch.object(orders.OrderResponse, "model_validate", return_value={"id": 12}) as model_validate,
        ):
            await orders.apply_refund(
                12,
                body=RefundRequest(reason="用户申请退款"),
                db=db,
                user=user,
            )

        apply_refund.assert_awaited_once_with(
            db,
            12,
            7,
            reason="用户申请退款",
            order_item_ids=None,
        )
        get_order_detail.assert_awaited_once_with(db, 12, user_id=7)
        model_validate.assert_called_once_with(order_detail)


if __name__ == "__main__":
    unittest.main()
