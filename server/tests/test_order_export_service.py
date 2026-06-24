import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class FakeDb:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index

    async def refresh(self, obj):
        return None


class OrderExportServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services import order_export_service

        self.service = order_export_service

    async def test_create_export_task_sync_writes_private_file_and_log(self):
        db = FakeDb()
        order = SimpleNamespace(
            order_no="YY202606180001",
            status="paid",
            payment_status="paid",
            actual_amount=123.45,
            created_at="2026-06-18T12:00:00",
            source_channel="poster",
            user=SimpleNamespace(nickname="张三", phone="13800000000"),
            items=[SimpleNamespace(product_id=18, product_name="林间营位", date="2026-07-01", quantity=1)],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with (
                patch.object(self.service, "PRIVATE_EXPORT_DIR", Path(tmp_dir)),
                patch.object(self.service.order_service, "list_orders", AsyncMock(return_value=([order], 1))),
                patch.object(self.service, "_generate_task_no", return_value="EXP202606180001"),
            ):
                task = await self.service.create_order_export_task(
                    db,
                    site_id=1,
                    filters={"status": "paid"},
                    file_format="csv",
                    include_sensitive=False,
                    created_by=3,
                )

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.row_count, 1)
        self.assertIsNotNone(task.file_path)
        self.assertNotIn("/images/", task.file_path)
        self.assertTrue(Path(task.file_path).name.endswith(".csv"))
        operation_logs = [obj for obj in db.added if obj.__class__.__name__ == "OperationLog"]
        self.assertEqual(operation_logs[0].action, "order_export")
        self.assertEqual(operation_logs[0].detail["row_count"], 1)
        self.assertEqual(operation_logs[0].detail["filters"], {"status": "paid"})

    async def test_get_download_path_requires_same_site_and_completed_status(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_file = Path(tmp_dir) / "orders.csv"
            export_file.write_text("订单号\nYY202606180001\n", encoding="utf-8")
            completed = SimpleNamespace(
                site_id=1,
                status="completed",
                file_path=str(export_file),
                expires_at=None,
            )
            with patch.object(self.service, "get_export_task", AsyncMock(return_value=completed)):
                path = await self.service.get_export_download_path(object(), site_id=1, task_id=7)
            self.assertEqual(path, export_file)

        expired = SimpleNamespace(site_id=1, status="expired", file_path="/tmp/private/orders.csv", expires_at=None)
        with patch.object(self.service, "get_export_task", AsyncMock(return_value=expired)):
            with self.assertRaises(Exception):
                await self.service.get_export_download_path(object(), site_id=1, task_id=7)


if __name__ == "__main__":
    unittest.main()
