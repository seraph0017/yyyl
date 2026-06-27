import unittest
from datetime import date
from types import SimpleNamespace


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def scalar(self):
        return self.value

    def all(self):
        return self.value


class FakeScalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeRowsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return FakeScalars(self.values)

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, *execute_values):
        self.execute_values = list(execute_values)
        self.added = []
        self.flush_count = 0

    async def execute(self, query):
        if not self.execute_values:
            raise AssertionError(f"unexpected query: {query}")
        value = self.execute_values.pop(0)
        if isinstance(value, list):
            return FakeRowsResult(value)
        return FakeScalarResult(value)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_count += 1


class CampMapServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_summarize_page_view_stats_aggregates_full_query(self):
        from services import camp_map_service

        db = FakeDb([(120, 2000, 600)])

        summary = await camp_map_service.summarize_page_view_stats(
            db,
            site_id=2,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 26),
        )

        self.assertEqual(summary["record_count"], 120)
        self.assertEqual(summary["view_count"], 2000)
        self.assertEqual(summary["user_count"], 600)

    async def test_record_zone_click_increments_linked_zone(self):
        from services import camp_map_service

        row = SimpleNamespace(
            id=12,
            click_count=4,
            link_type="product",
            link_target="88",
            link_label="查看营位",
        )
        db = FakeDb(row)

        result = await camp_map_service.record_zone_click(db, zone_id=12, site_id=2)

        self.assertEqual(result["click_count"], 4)
        self.assertEqual(result["link_type"], "product")
        self.assertEqual(result["link_target"], "88")
        self.assertEqual(db.flush_count, 1)

    async def test_record_page_view_creates_and_updates_daily_stat(self):
        from services import camp_map_service

        created_stat = SimpleNamespace(
            id=1,
            site_id=2,
            page_key="camp-map",
            page_title="营地地图",
            stat_date=date(2026, 6, 26),
            view_count=1,
            user_count=1,
        )
        create_db = FakeDb(created_stat)
        stat = await camp_map_service.record_page_view(
            create_db,
            site_id=2,
            page_key="camp-map",
            page_title="营地地图",
            user_id=101,
            stat_date=date(2026, 6, 26),
        )

        self.assertEqual(stat.site_id, 2)
        self.assertEqual(stat.page_key, "camp-map")
        self.assertEqual(stat.view_count, 1)
        self.assertEqual(stat.user_count, 1)
        self.assertEqual(len(create_db.added), 0)
        self.assertEqual(create_db.flush_count, 1)

        updated_stat = SimpleNamespace(
            id=1,
            site_id=2,
            page_key="camp-map",
            page_title="营地地图新版",
            stat_date=date(2026, 6, 26),
            view_count=2,
            user_count=1,
        )
        update_db = FakeDb(updated_stat)
        updated = await camp_map_service.record_page_view(
            update_db,
            site_id=2,
            page_key="camp-map",
            page_title="营地地图新版",
            user_id=None,
            stat_date=date(2026, 6, 26),
        )

        self.assertEqual(updated.view_count, 2)
        self.assertEqual(updated.user_count, 1)
        self.assertEqual(updated.page_title, "营地地图新版")
        self.assertEqual(len(update_db.added), 0)
        self.assertEqual(update_db.flush_count, 1)


if __name__ == "__main__":
    unittest.main()
