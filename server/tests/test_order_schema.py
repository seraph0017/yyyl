import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from models.order import Order
from services.order_service import _attach_order_display_fields, _resolve_primary_identity_id
from schemas.order import MockPayRequest, OrderCreateRequest, OrderResponse


class OrderCreateRequestTest(unittest.TestCase):
    def test_accepts_legacy_direct_order_payload(self):
        request = OrderCreateRequest.model_validate(
            {
                "product_id": 2,
                "dates": ["2026-06-12"],
                "quantity": 1,
                "identity_id": 5,
            }
        )

        self.assertEqual(len(request.items), 1)
        self.assertEqual(request.items[0].product_id, 2)
        self.assertEqual(request.items[0].quantity, 1)
        self.assertEqual(request.items[0].identity_ids, [5])
        self.assertTrue(request.disclaimer_signed)

    def test_keeps_explicit_legacy_disclaimer_value(self):
        request = OrderCreateRequest.model_validate(
            {
                "product_id": 2,
                "dates": ["2026-06-12"],
                "quantity": 1,
                "disclaimer_signed": False,
            }
        )

        self.assertFalse(request.disclaimer_signed)

    def test_mock_pay_accepts_legacy_action_fail(self):
        request = MockPayRequest.model_validate({"action": "fail"})

        self.assertFalse(request.success)

    def test_mock_pay_accepts_legacy_action_success(self):
        request = MockPayRequest.model_validate({"action": "success"})

        self.assertTrue(request.success)

    def test_order_model_exposes_preloaded_user_phone(self):
        order = Order()
        order.__dict__["user"] = SimpleNamespace(nickname="露营用户", phone="13800138000")

        self.assertEqual(order.user_nickname, "露营用户")
        self.assertEqual(order.user_phone, "13800138000")
        self.assertEqual(order.user_phone_masked, "138****8000")

    def test_order_response_includes_user_and_order_item_display_fields(self):
        now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
        order_item = SimpleNamespace(
            id=11,
            order_id=22,
            product_id=33,
            sku_id=44,
            inventory_pool_id=None,
            date=None,
            time_slot="15:00-16:00",
            quantity=2,
            unit_price=Decimal("88.00"),
            actual_price=Decimal("176.00"),
            identity_id=55,
            parent_item_id=None,
            refund_status="none",
            created_at=now,
            product_name="皮划艇活动",
            product_image="/images/activity/kayak.jpg",
            cover_image="/images/activity/fallback.jpg",
            sku_spec_values={"类型": "一大一小"},
            identity_name="张三",
            remark="靠近码头集合",
        )
        order = SimpleNamespace(
            id=22,
            order_no="O202606300001",
            user_id=66,
            user_nickname="露营用户",
            user_phone="13800138000",
            user_phone_masked="138****8000",
            parent_order_id=None,
            order_type="daily_activity",
            status="paid",
            total_amount=Decimal("176.00"),
            discount_amount=Decimal("0.00"),
            actual_amount=Decimal("176.00"),
            deposit_amount=Decimal("0.00"),
            discount_type=None,
            discount_detail=None,
            payment_method="wechat_pay",
            payment_status="paid",
            payment_time=now,
            payment_no="4200000000000000000",
            times_card_id=None,
            times_consumed=None,
            address_id=None,
            shipping_no=None,
            shipping_status=None,
            remark="整单备注",
            expire_at=None,
            created_at=now,
            updated_at=now,
            items=[order_item],
            countdown_seconds=None,
        )

        response = OrderResponse.model_validate(order)

        self.assertEqual(response.user_phone_masked, "138****8000")
        self.assertEqual(response.items[0].product_image, "/images/activity/kayak.jpg")
        self.assertEqual(response.items[0].cover_image, "/images/activity/fallback.jpg")
        self.assertEqual(response.items[0].sku_spec_values, {"类型": "一大一小"})
        self.assertEqual(response.items[0].remark, "靠近码头集合")

    def test_order_create_request_keeps_address_id_for_shipping_goods(self):
        request = OrderCreateRequest.model_validate(
            {
                "items": [{"product_id": 88, "quantity": 1, "dates": []}],
                "address_id": 123,
            }
        )

        self.assertEqual(request.address_id, 123)


class OrderDisplayFieldsTest(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_primary_identity_id_rejects_other_users_identity(self):
        class _Scalars:
            def all(self):
                return []

        class _Result:
            def scalars(self):
                return _Scalars()

        class _Db:
            async def execute(self, _query):
                return _Result()

        with self.assertRaises(Exception) as context:
            await _resolve_primary_identity_id(
                _Db(),
                SimpleNamespace(id=66),
                [55],
            )

        self.assertEqual(context.exception.status_code, 400)

    async def test_resolve_primary_identity_id_returns_first_owned_identity(self):
        class _Scalars:
            def all(self):
                return [55, 56]

        class _Result:
            def scalars(self):
                return _Scalars()

        class _Db:
            async def execute(self, _query):
                return _Result()

        identity_id = await _resolve_primary_identity_id(
            _Db(),
            SimpleNamespace(id=66),
            [55, 56],
        )

        self.assertEqual(identity_id, 55)

    async def test_attach_order_display_fields_uses_sku_product_identity_and_order_remark(self):
        item = SimpleNamespace(
            product_id=33,
            sku_id=44,
            identity_id=55,
        )
        order = SimpleNamespace(
            user_id=66,
            items=[item],
            remark="靠近码头集合",
        )
        product = SimpleNamespace(
            id=33,
            name="皮划艇活动",
            images=[
                {"url": "/images/activity/fallback.jpg", "sort_order": 2},
                {"url": "/images/activity/main.jpg", "sort_order": 1},
            ],
        )
        sku = SimpleNamespace(
            id=44,
            image_url="/images/activity/sku.jpg",
            spec_values={"类型": "一大一小"},
        )
        identity = SimpleNamespace(id=55, user_id=66, name="张三")

        class _Scalars:
            def __init__(self, values):
                self._values = values

            def all(self):
                return self._values

        class _Result:
            def __init__(self, values):
                self._values = values

            def scalars(self):
                return _Scalars(self._values)

        class _Db:
            def __init__(self):
                self._results = [_Result([product]), _Result([sku]), _Result([identity])]

            async def execute(self, _query):
                return self._results.pop(0)

        await _attach_order_display_fields(_Db(), [order])

        self.assertEqual(item.product_name, "皮划艇活动")
        self.assertEqual(item.product_image, "/images/activity/sku.jpg")
        self.assertEqual(item.cover_image, "/images/activity/sku.jpg")
        self.assertEqual(item.sku_spec_values, {"类型": "一大一小"})
        self.assertEqual(item.identity_name, "张三")
        self.assertEqual(item.remark, "靠近码头集合")


if __name__ == "__main__":
    unittest.main()
