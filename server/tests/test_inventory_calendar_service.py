import unittest
from datetime import date
from types import SimpleNamespace


class InventoryCalendarServiceTest(unittest.TestCase):
    def test_missing_inventory_date_returns_closed_editable_cell(self):
        from services import inventory_calendar_service

        product = SimpleNamespace(id=12, name="湖畔营位", base_price=199)

        cell = inventory_calendar_service.build_inventory_calendar_cell(
            product=product,
            sku=None,
            current_date=date(2026, 7, 3),
            date_type="weekday",
            price=199,
            inventory=None,
            inventory_pool=None,
        )

        self.assertEqual(cell["product_id"], 12)
        self.assertEqual(cell["date"], date(2026, 7, 3))
        self.assertEqual(cell["inventory_source"], "inventory")
        self.assertIsNone(cell["inventory_id"])
        self.assertEqual(cell["total"], 0)
        self.assertEqual(cell["available"], 0)
        self.assertEqual(cell["locked"], 0)
        self.assertEqual(cell["sold"], 0)
        self.assertEqual(cell["status"], "closed")
        self.assertTrue(cell["editable"])

    def test_missing_inventory_date_keeps_requested_time_slot(self):
        from services import inventory_calendar_service

        product = SimpleNamespace(id=12, name="湖畔营位", base_price=199)

        cell = inventory_calendar_service.build_inventory_calendar_cell(
            product=product,
            sku=None,
            current_date=date(2026, 7, 3),
            date_type="weekday",
            price=199,
            inventory=None,
            inventory_pool=None,
            time_slot="AM",
        )

        self.assertEqual(cell["time_slot"], "AM")

    def test_shared_inventory_pool_cell_is_read_only_for_date_inventory(self):
        from services import inventory_calendar_service

        product = SimpleNamespace(id=12, name="湖畔营位", base_price=199)
        pool = SimpleNamespace(
            id=5,
            pool_code="POOL-LAKE",
            name="湖畔共享池",
            total=20,
            available=13,
            locked=2,
            sold=5,
            status="active",
        )

        cell = inventory_calendar_service.build_inventory_calendar_cell(
            product=product,
            sku=None,
            current_date=date(2026, 7, 4),
            date_type="weekend",
            price=259,
            inventory=None,
            inventory_pool=pool,
        )

        self.assertEqual(cell["inventory_source"], "inventory_pool")
        self.assertEqual(cell["inventory_pool_id"], 5)
        self.assertEqual(cell["inventory_pool_code"], "POOL-LAKE")
        self.assertEqual(cell["total"], 20)
        self.assertEqual(cell["available"], 13)
        self.assertEqual(cell["locked"], 2)
        self.assertEqual(cell["sold"], 5)
        self.assertEqual(cell["status"], "open")
        self.assertFalse(cell["editable"])
        self.assertIn("共享库存池", cell["edit_reason"])

    def test_shared_inventory_pool_cell_keeps_requested_time_slot(self):
        from services import inventory_calendar_service

        product = SimpleNamespace(id=12, name="湖畔营位", base_price=199)
        pool = SimpleNamespace(
            id=5,
            pool_code="POOL-LAKE",
            name="湖畔共享池",
            total=20,
            available=13,
            locked=2,
            sold=5,
            status="active",
        )

        cell = inventory_calendar_service.build_inventory_calendar_cell(
            product=product,
            sku=None,
            current_date=date(2026, 7, 4),
            date_type="weekend",
            price=259,
            inventory=None,
            inventory_pool=pool,
            time_slot="PM",
        )

        self.assertEqual(cell["time_slot"], "PM")

    def test_expand_batch_dates_supports_explicit_dates_and_weekday_filter(self):
        from services import inventory_calendar_service

        dates = inventory_calendar_service.expand_batch_dates(
            date_start=date(2026, 7, 1),
            date_end=date(2026, 7, 7),
            dates=None,
            weekdays=[0, 2, 4],
        )
        self.assertEqual(
            dates,
            [date(2026, 7, 1), date(2026, 7, 3), date(2026, 7, 6)],
        )

        explicit_dates = inventory_calendar_service.expand_batch_dates(
            date_start=None,
            date_end=None,
            dates=[date(2026, 7, 5), date(2026, 7, 5), date(2026, 7, 2)],
            weekdays=None,
        )
        self.assertEqual(explicit_dates, [date(2026, 7, 2), date(2026, 7, 5)])

    def test_recompute_available_rejects_total_below_locked_and_sold(self):
        from services import inventory_calendar_service

        self.assertEqual(
            inventory_calendar_service.recompute_available(total=10, locked=2, sold=3),
            5,
        )

        with self.assertRaises(ValueError):
            inventory_calendar_service.recompute_available(total=4, locked=2, sold=3)

    def test_batch_payload_for_pool_bound_target_is_rejected_before_plain_inventory_write(self):
        from services import inventory_calendar_service

        targets = [SimpleNamespace(product_id=12, sku_id=None)]
        bound_pool_map = {
            (12, None): SimpleNamespace(id=5, pool_code="POOL-LAKE", name="湖畔共享池")
        }

        with self.assertRaises(ValueError) as ctx:
            inventory_calendar_service.ensure_targets_not_pool_bound(
                targets,
                bound_pool_map=bound_pool_map,
            )

        self.assertIn("共享库存池", str(ctx.exception))

    def test_inactive_pool_binding_still_blocks_plain_inventory_write(self):
        from services.inventory_pool_service import resolve_declared_inventory_pool

        pools = {
            5: SimpleNamespace(id=5, pool_code="POOL-LAKE", status="inactive", is_deleted=False)
        }
        bindings = [
            SimpleNamespace(
                id=1,
                inventory_pool_id=5,
                product_id=12,
                sku_id=None,
                activity_session_id=None,
                rental_asset_id=None,
                status="active",
                is_deleted=False,
                priority=100,
            )
        ]

        pool = resolve_declared_inventory_pool(
            bindings,
            pools=pools,
            product_id=12,
            sku_id=None,
        )

        self.assertIsNotNone(pool)
        self.assertEqual(pool.id, 5)

    def test_inactive_pool_calendar_cell_remains_shared_and_read_only(self):
        from services import inventory_calendar_service

        product = SimpleNamespace(id=12, name="湖畔营位", base_price=199)
        pool = SimpleNamespace(
            id=5,
            pool_code="POOL-LAKE",
            name="湖畔共享池",
            total=20,
            available=0,
            locked=2,
            sold=18,
            status="inactive",
        )

        cell = inventory_calendar_service.build_inventory_calendar_cell(
            product=product,
            sku=None,
            current_date=date(2026, 7, 4),
            date_type="weekend",
            price=259,
            inventory=None,
            inventory_pool=pool,
        )

        self.assertEqual(cell["inventory_source"], "inventory_pool")
        self.assertEqual(cell["status"], "closed")
        self.assertFalse(cell["editable"])


if __name__ == "__main__":
    unittest.main()
