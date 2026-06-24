import unittest


class V17ModelContractTest(unittest.TestCase):
    def test_v17_models_are_registered_in_metadata(self):
        import models  # noqa: F401
        from models.base import Base

        expected_tables = {
            "mini_program_qrcode",
            "mini_program_qrcode_scan_log",
            "refund_record",
            "refund_record_item",
            "finance_settlement",
            "order_export_task",
        }

        self.assertTrue(expected_tables.issubset(set(Base.metadata.tables)))

    def test_v17_order_finance_columns_are_declared(self):
        import models  # noqa: F401
        from models.finance import FinanceTransaction
        from models.order import Order, OrderItem

        self.assertIn("source_qrcode_id", Order.__table__.columns)
        self.assertIn("source_channel", Order.__table__.columns)
        self.assertIn("source_scanned_at", Order.__table__.columns)
        self.assertIn("settled_amount", Order.__table__.columns)
        self.assertIn("settlement_status", Order.__table__.columns)
        self.assertIn("refund_status", Order.__table__.columns)
        self.assertIn("refund_status", OrderItem.__table__.columns)
        self.assertIn("refund_record_id", FinanceTransaction.__table__.columns)


class V17SchemaContractTest(unittest.TestCase):
    def test_qrcode_create_schema_accepts_product_target(self):
        from schemas.qrcode import QrcodeCreateRequest

        request = QrcodeCreateRequest.model_validate(
            {
                "target_type": "product",
                "target_key": "123",
                "title": "湖畔营位 A 区",
                "channel": "poster",
            }
        )

        self.assertEqual(request.target_type, "product")
        self.assertEqual(request.channel, "poster")

    def test_refund_create_schema_accepts_keep_order_partial_refund(self):
        from schemas.refund import RefundCreateRequest

        request = RefundCreateRequest.model_validate(
            {
                "refund_mode": "partial",
                "order_action": "keep_order",
                "refund_amount": "50.00",
                "release_inventory": False,
                "reason": "服务体验补偿",
                "items": [
                    {"order_item_id": 1001, "refund_amount": "50.00", "quantity": 1}
                ],
            }
        )

        self.assertEqual(request.refund_mode, "partial")
        self.assertEqual(request.order_action, "keep_order")
        self.assertFalse(request.release_inventory)

    def test_order_create_schema_accepts_qrcode_attribution(self):
        from schemas.order import OrderCreateRequest

        request = OrderCreateRequest.model_validate(
            {
                "items": [
                    {
                        "product_id": 2,
                        "quantity": 1,
                        "dates": ["2026-06-20"],
                    }
                ],
                "source_qrcode_id": 9,
                "source_channel": "poster",
                "source_scanned_at": "2026-06-18T12:00:00+00:00",
            }
        )

        self.assertEqual(request.source_qrcode_id, 9)
        self.assertEqual(request.source_channel, "poster")
        self.assertIsNotNone(request.source_scanned_at)

    def test_order_create_schema_accepts_non_campsite_without_dates(self):
        from schemas.order import OrderCreateRequest

        request = OrderCreateRequest.model_validate(
            {
                "items": [
                    {
                        "product_id": 8,
                        "quantity": 2,
                        "dates": [],
                    }
                ],
            }
        )

        self.assertEqual(request.items[0].dates, [])


class V17RouteContractTest(unittest.TestCase):
    def test_v17_routes_are_registered(self):
        from main import app

        paths = {route.path for route in app.routes}

        expected_paths = {
            "/api/v1/admin/qrcodes",
            "/api/v1/qrcodes/resolve",
            "/api/v1/admin/orders/{order_id}/refunds",
            "/api/v1/admin/refunds",
            "/api/v1/admin/finance/settlements",
            "/api/v1/admin/orders/export",
            "/api/v1/admin/orders/export-tasks",
            "/api/v1/admin/cms/pages/{page_id}/qrcode",
        }

        self.assertTrue(expected_paths.issubset(paths))


if __name__ == "__main__":
    unittest.main()
