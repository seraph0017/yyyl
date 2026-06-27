import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from services import order_service


class OrderServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_order_detail_filters_by_site_id_when_provided(self):
        order = SimpleNamespace(id=12)
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=lambda: order)
            )
        )

        result = await order_service.get_order_detail(db, order_id=12, user_id=7, site_id=2)

        self.assertIs(result, order)
        statement = db.execute.await_args.args[0]
        sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn('"order".site_id = 2', sql)

    async def test_initiate_payment_maps_wechat_pay_error_to_business_error(self):
        db = SimpleNamespace(flush=AsyncMock())
        order = SimpleNamespace(
            id=12,
            site_id=1,
            status="pending_payment",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

        with (
            patch.object(order_service, "_get_user_order", AsyncMock(return_value=order)),
            patch.object(
                order_service.wechat_pay_service,
                "create_jsapi_prepay",
                AsyncMock(side_effect=order_service.wechat_pay_service.WechatPayError("商户 API 私钥读取失败")),
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await order_service.initiate_payment(db, order_id=12, user_id=7)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.detail["code"], 50201)
        self.assertIn("微信支付暂不可用", ctx.exception.detail["message"])
        db.flush.assert_not_awaited()

    async def test_initiate_payment_returns_payment_params_on_success(self):
        db = SimpleNamespace(flush=AsyncMock())
        order = SimpleNamespace(
            id=12,
            site_id=1,
            status="pending_payment",
            expire_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        payment_params = {"appId": "wx-test"}

        with (
            patch.object(order_service, "_get_user_order", AsyncMock(return_value=order)),
            patch.object(
                order_service.wechat_pay_service,
                "create_jsapi_prepay",
                AsyncMock(return_value=payment_params),
            ) as create_prepay,
        ):
            result = await order_service.initiate_payment(db, order_id=12, user_id=7, payment_method="wechat_pay")

        self.assertEqual(result, payment_params)
        create_prepay.assert_awaited_once_with(order, site_id=1)
        self.assertEqual(order.payment_method, "wechat_pay")
        db.flush.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
