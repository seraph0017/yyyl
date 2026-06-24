import unittest
from datetime import date, datetime, timezone

from sqlalchemy.dialects import postgresql


class OrderFilterQueryTest(unittest.TestCase):
    def setUp(self):
        from services import order_service

        self.service = order_service

    def compile_query(self, query):
        return str(
            query.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

    def test_build_order_list_query_includes_v17_advanced_filters(self):
        query = self.service.build_order_list_query(
            site_id=1,
            product_id=18,
            product_type="daily_camping",
            booking_date_start=date(2026, 7, 1),
            booking_date_end=date(2026, 7, 3),
            payment_time_start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            payment_time_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
            amount_min=100,
            amount_max=500,
            verify_status="verified",
            source_channel="poster",
        )
        sql = self.compile_query(query)

        self.assertIn('"order".site_id = 1', sql)
        self.assertIn("order_item.product_id = 18", sql)
        self.assertIn("product.type = 'daily_camping'", sql)
        self.assertIn("order_item.date >= '2026-07-01'", sql)
        self.assertIn("order_item.date <= '2026-07-03'", sql)
        self.assertIn('"order".payment_time >= ', sql)
        self.assertIn('"order".payment_time <= ', sql)
        self.assertIn('"order".actual_amount >= 100', sql)
        self.assertIn('"order".actual_amount <= 500', sql)
        self.assertIn("ticket.verify_status = 'verified'", sql)
        self.assertIn('"order".source_channel = \'poster\'', sql)

    def test_build_order_list_query_keyword_searches_order_user_and_product(self):
        query = self.service.build_order_list_query(site_id=1, keyword="张三")
        sql = self.compile_query(query)

        self.assertIn('"order".order_no ILIKE', sql)
        self.assertIn('"user".nickname ILIKE', sql)
        self.assertIn('"user".phone ILIKE', sql)
        self.assertIn("product.name ILIKE", sql)


if __name__ == "__main__":
    unittest.main()
