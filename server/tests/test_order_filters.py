import unittest
import inspect
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

    def test_list_orders_counts_and_pages_by_distinct_order_id(self):
        source = inspect.getsource(self.service.list_orders)

        self.assertIn("with_only_columns(Order.id).order_by(None).distinct().subquery()", source)
        self.assertIn("select(func.count()).select_from(distinct_order_ids)", source)
        self.assertIn("select(distinct_order_ids.c.id)", source)
        self.assertIn("id_query.offset(offset).limit(page_size)", source)
        self.assertIn("Order.id.in_(order_ids)", source)
        self.assertNotIn("select(func.count()).select_from(query.subquery())", source)


if __name__ == "__main__":
    unittest.main()
