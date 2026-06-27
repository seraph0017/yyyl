import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from routers import payments


class PaymentRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_wechat_payment_notify_parses_notification_and_updates_order(self):
        request = SimpleNamespace(
            headers={"x-site-id": "1"},
            body=AsyncMock(return_value=b'{"id":"notify"}'),
        )
        db = object()
        transaction = {
            "out_trade_no": "YY202606140001",
            "transaction_id": "4200001",
            "trade_state": "SUCCESS",
        }

        with (
            patch.object(payments.wechat_pay_service, "parse_notification_body", AsyncMock(return_value=transaction)) as parse_body,
            patch.object(payments.order_service, "handle_wechat_payment_notification", AsyncMock()) as handle_notify,
        ):
            result = await payments.wechat_payment_notify(request, db=db)

        self.assertEqual(result, {"code": "SUCCESS", "message": "成功"})
        parse_body.assert_awaited_once_with('{"id":"notify"}', dict(request.headers), site_id=1)
        handle_notify.assert_awaited_once_with(db, transaction)

    async def test_wechat_refund_notify_parses_notification_and_updates_order(self):
        request = SimpleNamespace(
            headers={"x-site-id": "1"},
            body=AsyncMock(return_value=b'{"id":"refund"}'),
        )
        db = object()
        refund = {"out_trade_no": "YY202606140001", "refund_status": "SUCCESS"}

        with (
            patch.object(payments.wechat_pay_service, "parse_notification_body", AsyncMock(return_value=refund)) as parse_body,
            patch.object(payments.refund_service, "handle_wechat_refund_notification", AsyncMock()) as handle_notify,
        ):
            result = await payments.wechat_refund_notify(request, db=db)

        self.assertEqual(result, {"code": "SUCCESS", "message": "成功"})
        parse_body.assert_awaited_once_with('{"id":"refund"}', dict(request.headers), site_id=1)
        handle_notify.assert_awaited_once_with(db, refund)

    async def test_wechat_payment_notify_acks_only_late_or_status_conflict(self):
        request = SimpleNamespace(
            headers={"x-site-id": "1"},
            body=AsyncMock(return_value=b'{"id":"notify"}'),
        )
        db = object()
        transaction = {
            "out_trade_no": "YY202606140001",
            "transaction_id": "4200001",
            "trade_state": "SUCCESS",
        }

        with (
            patch.object(payments.wechat_pay_service, "parse_notification_body", AsyncMock(return_value=transaction)),
            patch.object(
                payments.order_service,
                "handle_wechat_payment_notification",
                AsyncMock(side_effect=HTTPException(status_code=400, detail={"code": 40902, "message": "订单状态不允许支付"})),
            ),
        ):
            result = await payments.wechat_payment_notify(request, db=db)

        self.assertEqual(result, {"code": "SUCCESS", "message": "已接收"})

    async def test_wechat_payment_notify_does_not_ack_unexpected_http_exception(self):
        request = SimpleNamespace(
            headers={"x-site-id": "1"},
            body=AsyncMock(return_value=b'{"id":"notify"}'),
        )
        db = object()
        transaction = {
            "out_trade_no": "YY202606140001",
            "transaction_id": "4200001",
            "trade_state": "SUCCESS",
        }

        with (
            patch.object(payments.wechat_pay_service, "parse_notification_body", AsyncMock(return_value=transaction)),
            patch.object(
                payments.order_service,
                "handle_wechat_payment_notification",
                AsyncMock(side_effect=HTTPException(status_code=500, detail={"code": 50001, "message": "库存确认失败"})),
            ),
        ):
            with self.assertRaises(HTTPException):
                await payments.wechat_payment_notify(request, db=db)


if __name__ == "__main__":
    unittest.main()
