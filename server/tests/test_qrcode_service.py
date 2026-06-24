import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


class FakeDb:
    def __init__(self):
        self.added = []
        self.flushed = False
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def execute(self, statement):
        return SimpleNamespace(scalar_one_or_none=lambda: None, scalar_one=lambda: 0)


class QrcodeServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services import qrcode_service

        self.service = qrcode_service

    def test_build_target_path_uses_only_whitelisted_pages(self):
        cases = {
            ("product", "18"): "/pages/product-detail/index?id=18",
            ("activity_product", "19"): "/pages/product-detail/index?id=19",
            ("category", "tent"): "/pages/category/index?category=tent",
            ("custom_page", "brand-story"): "/pages/cms-page/index?page_code=brand-story",
            ("activity_page", "summer-sale"): "/pages/cms-page/index?page_code=summer-sale",
        }

        for (target_type, target_key), expected in cases.items():
            with self.subTest(target_type=target_type):
                self.assertEqual(
                    self.service.build_target_path(target_type, target_key),
                    expected,
                )

        with self.assertRaises(HTTPException):
            self.service.build_target_path("external", "https://example.com")

    async def test_create_or_reuse_qrcode_reuses_existing_target_channel(self):
        from schemas.qrcode import QrcodeCreateRequest

        existing = SimpleNamespace(
            id=7,
            site_id=1,
            target_type="product",
            target_key="18",
            title="露营套餐",
            channel="poster",
            status="active",
        )
        db = FakeDb()
        body = QrcodeCreateRequest(
            target_type="product",
            target_key="18",
            title="露营套餐",
            channel="poster",
        )

        with (
            patch.object(self.service, "_find_existing_qrcode", AsyncMock(return_value=existing)) as find_existing,
            patch.object(self.service, "_create_wechat_qrcode_image", AsyncMock()) as create_image,
        ):
            result = await self.service.create_or_reuse_qrcode(
                db,
                site_id=1,
                body=body,
                generated_by=3,
            )

        self.assertIs(result, existing)
        find_existing.assert_awaited_once_with(
            db,
            site_id=1,
            target_type="product",
            target_key="18",
            channel="poster",
        )
        create_image.assert_not_awaited()
        self.assertEqual(db.added, [])

    async def test_create_or_reuse_qrcode_creates_new_record_with_wechat_image(self):
        from schemas.qrcode import QrcodeCreateRequest

        db = FakeDb()
        body = QrcodeCreateRequest(
            target_type="category",
            target_key="tent",
            title="帐篷分类",
            channel="default",
        )

        with (
            patch.object(self.service, "_find_existing_qrcode", AsyncMock(return_value=None)),
            patch.object(self.service, "_generate_unique_short_code", AsyncMock(return_value="abc123")),
            patch.object(self.service, "_create_wechat_qrcode_image", AsyncMock(return_value="/images/qrcodes/1/abc123.png")) as create_image,
        ):
            result = await self.service.create_or_reuse_qrcode(
                db,
                site_id=1,
                body=body,
                generated_by=3,
            )

        self.assertEqual(result.target_type, "category")
        self.assertEqual(result.target_key, "tent")
        self.assertEqual(result.path, "/pages/category/index?category=tent")
        self.assertEqual(result.short_code, "abc123")
        self.assertEqual(result.scene, "abc123")
        self.assertEqual(result.image_url, "/images/qrcodes/1/abc123.png")
        self.assertEqual(result.generated_by, 3)
        self.assertTrue(db.flushed)
        create_image.assert_awaited_once_with(site_id=1, scene="abc123")

    async def test_create_or_reuse_qrcode_rejects_unpublished_cms_page(self):
        from schemas.qrcode import QrcodeCreateRequest

        db = FakeDb()
        body = QrcodeCreateRequest(
            target_type="custom_page",
            target_key="brand-story",
            title="品牌故事",
        )

        with (
            patch.object(self.service, "_find_existing_qrcode", AsyncMock(return_value=None)),
            patch.object(self.service.cms_service, "get_published_page", AsyncMock(return_value=None)),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await self.service.create_or_reuse_qrcode(db, site_id=1, body=body)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(db.added, [])

    async def test_resolve_qrcode_increments_usage_and_logs_scan(self):
        qrcode = SimpleNamespace(
            id=11,
            site_id=1,
            target_type="product",
            target_key="18",
            title="露营套餐",
            path="/pages/product-detail/index?id=18",
            channel="poster",
            status="active",
            usage_count=2,
            last_used_at=None,
        )
        db = FakeDb()

        with patch.object(self.service, "_find_qrcode_by_scene", AsyncMock(return_value=qrcode)):
            result = await self.service.resolve_qrcode(
                db,
                site_id=1,
                scene="abc123",
                user_id=8,
                openid="openid-test",
                client_info={"platform": "ios"},
            )

        self.assertEqual(result.qr_code_id, 11)
        self.assertEqual(result.path, "/pages/product-detail/index?id=18")
        self.assertEqual(qrcode.usage_count, 3)
        self.assertIsNotNone(qrcode.last_used_at)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].qr_code_id, 11)
        self.assertEqual(db.added[0].raw_scene, "abc123")

    async def test_resolve_qrcode_rejects_inactive_code(self):
        qrcode = SimpleNamespace(status="inactive")

        with patch.object(self.service, "_find_qrcode_by_scene", AsyncMock(return_value=qrcode)):
            with self.assertRaises(HTTPException) as ctx:
                await self.service.resolve_qrcode(object(), site_id=1, scene="abc123")

        self.assertEqual(ctx.exception.status_code, 410)

    def test_validate_wechat_qrcode_image_rejects_non_image_or_empty_body(self):
        self.service.validate_wechat_qrcode_image(
            content_type="image/png",
            body=b"\x89PNG\r\n",
        )

        with self.assertRaises(self.service.QrcodeServiceError):
            self.service.validate_wechat_qrcode_image(
                content_type="application/json",
                body=b'{"errcode":40001}',
            )

        with self.assertRaises(self.service.QrcodeServiceError):
            self.service.validate_wechat_qrcode_image(
                content_type="image/png",
                body=b"",
            )

    def test_get_wechat_mini_program_config_prefers_site_mapping(self):
        with patch.object(
            self.service.settings,
            "WECHAT_APPS",
            '{"2":{"app_id":"wx-site-2","app_secret":"secret-2"}}',
        ):
            config = self.service.get_wechat_mini_program_config(2)

        self.assertEqual(config.app_id, "wx-site-2")
        self.assertEqual(config.app_secret, "secret-2")


if __name__ == "__main__":
    unittest.main()
