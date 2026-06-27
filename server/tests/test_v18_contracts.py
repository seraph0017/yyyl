import asyncio
import unittest
import inspect
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class V18InventoryPoolContractTest(unittest.TestCase):
    def test_inventory_pool_models_are_registered_in_metadata(self):
        import models  # noqa: F401
        from models.base import Base

        expected_tables = {
            "inventory_pool",
            "inventory_pool_binding",
        }

        self.assertTrue(expected_tables.issubset(set(Base.metadata.tables)))

    def test_inventory_pool_binding_supports_cross_product_targets(self):
        from models.inventory_pool import InventoryPool, InventoryPoolBinding

        pool_columns = set(InventoryPool.__table__.columns.keys())
        binding_columns = set(InventoryPoolBinding.__table__.columns.keys())

        self.assertTrue(
            {
                "site_id",
                "pool_code",
                "name",
                "pool_type",
                "total",
                "available",
                "locked",
                "sold",
                "status",
            }.issubset(pool_columns)
        )
        self.assertTrue(
            {
                "inventory_pool_id",
                "site_id",
                "product_id",
                "sku_id",
                "activity_session_id",
                "rental_asset_id",
                "priority",
                "status",
            }.issubset(binding_columns)
        )

    def test_inventory_pool_numbers_must_match_total(self):
        from services.inventory_pool_service import validate_pool_numbers

        validate_pool_numbers(total=10, available=6, locked=1, sold=3)

        with self.assertRaises(ValueError):
            validate_pool_numbers(total=10, available=7, locked=1, sold=3)

    def test_inventory_pool_creation_forces_clean_initial_stock_state(self):
        from services.inventory_pool_service import normalize_initial_pool_numbers

        self.assertEqual(
            normalize_initial_pool_numbers({"total": 10}),
            {"total": 10, "available": 10, "locked": 0, "sold": 0},
        )

        invalid_payloads = [
            {"total": 10, "available": 9},
            {"total": 10, "locked": 1},
            {"total": 10, "sold": 1},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    normalize_initial_pool_numbers(payload)

    def test_inventory_pool_binding_requires_exactly_one_target(self):
        from services.inventory_pool_service import validate_exactly_one_binding_target

        validate_exactly_one_binding_target({
            "product_id": 8,
            "sku_id": None,
            "activity_session_id": None,
            "rental_asset_id": None,
        })

        with self.assertRaises(ValueError):
            validate_exactly_one_binding_target({
                "product_id": 8,
                "sku_id": 9,
                "activity_session_id": None,
                "rental_asset_id": None,
            })
        with self.assertRaises(ValueError):
            validate_exactly_one_binding_target({
                "product_id": None,
                "sku_id": None,
                "activity_session_id": None,
                "rental_asset_id": None,
            })

    def test_order_item_tracks_locked_inventory_pool(self):
        from models.order import OrderItem

        columns = set(OrderItem.__table__.columns.keys())
        self.assertIn("inventory_pool_id", columns)

        index_columns = {
            tuple(column.name for column in index.columns)
            for index in OrderItem.__table__.indexes
        }
        self.assertIn(("inventory_pool_id",), index_columns)

    def test_annual_card_order_tracks_business_snapshot_and_card_order_is_unique(self):
        from models.member import AnnualCard
        from models.order import Order

        self.assertIn("biz_data", Order.__table__.columns)
        order_indexes = {
            (index.name, tuple(column.name for column in index.columns), index.unique)
            for index in Order.__table__.indexes
        }
        self.assertIn(
            ("uq_order_annual_pending_active", ("user_id", "site_id"), True),
            order_indexes,
        )
        annual_card_indexes = {
            (index.name, tuple(column.name for column in index.columns), index.unique)
            for index in AnnualCard.__table__.indexes
        }
        self.assertIn(("uq_ac_order", ("order_id",), True), annual_card_indexes)

    def test_refund_record_tracks_inventory_release_idempotency(self):
        from models.refund import RefundRecord

        self.assertIn("inventory_released", RefundRecord.__table__.columns)
        refund_indexes = {
            (index.name, tuple(column.name for column in index.columns), index.unique)
            for index in RefundRecord.__table__.indexes
        }
        self.assertIn(("idx_refund_order", ("order_id",), False), refund_indexes)
        self.assertIn(("uq_refund_record_active_order", ("order_id",), True), refund_indexes)

    def test_finance_transaction_refund_record_is_unique(self):
        from models.finance import FinanceTransaction

        finance_indexes = {
            (index.name, tuple(column.name for column in index.columns), index.unique)
            for index in FinanceTransaction.__table__.indexes
        }
        self.assertIn(("uq_ft_refund_record", ("refund_record_id",), True), finance_indexes)

    def test_concurrency_guard_migration_preflights_existing_duplicates(self):
        migration = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("alembic", "versions", "0a1b2c3d4e5f_v1_8_annual_card_refund_concurrency_guard.py")
        )

        source = migration.read_text(encoding="utf-8")
        self.assertIn("_assert_no_duplicate_pending_annual_orders", source)
        self.assertIn("_assert_no_duplicate_active_refunds", source)
        self.assertIn("_assert_no_duplicate_refund_transactions", source)
        self.assertIn("expire_at <= now()", source)
        annual_index_source = source.split('op.create_index(\n        "uq_order_annual_pending_active"', 1)[1]
        annual_index_source = annual_index_source.split("op.create_index(", 1)[0]
        self.assertNotIn("expire_at > now()", annual_index_source)

    def test_ticket_verification_log_model_is_registered(self):
        import models  # noqa: F401
        from models.base import Base
        from models.order import Ticket, TicketVerifyLog

        self.assertIn("ticket_verify_log", Base.metadata.tables)
        self.assertIn("site_id", Ticket.__table__.columns)
        columns = set(TicketVerifyLog.__table__.columns.keys())
        self.assertTrue(
            {
                "site_id",
                "ticket_id",
                "order_id",
                "order_item_id",
                "staff_id",
                "verify_result",
                "failure_reason",
                "device_info",
            }.issubset(columns)
        )

    def test_timeout_task_releases_shared_inventory_pool_locks(self):
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("tasks", "inventory.py")
            .read_text(encoding="utf-8")
        )
        self.assertIn("inventory_pool_id", source)
        self.assertIn("InventoryPool", source)
        self.assertIn("pool.locked", source)
        self.assertIn("pool.available", source)

    def test_refund_success_releases_shared_inventory_once(self):
        from services import refund_service

        source = inspect.getsource(refund_service.apply_refund_success)
        self.assertIn("_release_refund_record_inventory", source)
        self.assertIn("inventory_released", source)

    def test_cart_checkout_reuses_order_service_inventory_locking(self):
        from routers import cart

        source = inspect.getsource(cart.checkout)
        self.assertIn("order_service.create_order", source)
        self.assertNotIn("OrderItem(", source)
        self.assertNotIn("Order(", source)

    def test_cart_checkout_passes_disclaimer_signed_to_order_service(self):
        from routers import cart
        from schemas.cart import CartCheckoutRequest

        request = CartCheckoutRequest.model_validate(
            {
                "item_ids": [1, 2],
                "disclaimer_signed": True,
            }
        )
        source = inspect.getsource(cart.checkout)

        self.assertTrue(request.disclaimer_signed)
        self.assertIn("disclaimer_signed = body.disclaimer_signed", source)
        self.assertIn("disclaimer_signed=disclaimer_signed", source)


class V18UnifiedProductEditorContractTest(unittest.TestCase):
    def test_admin_product_routes_and_schema_support_full_editor_payload(self):
        from routers import products
        from schemas.product import ProductUpdate

        routes_source = inspect.getsource(products)
        self.assertIn('@router.get("/api/v1/admin/products/{product_id}"', routes_source)
        self.assertIn('@router.delete("/api/v1/admin/products/{product_id}"', routes_source)
        self.assertIn('@router.patch("/api/v1/admin/products/{product_id}/status"', routes_source)

        fields = set(ProductUpdate.model_fields.keys())
        self.assertIn("type", fields)
        self.assertIn("skus", fields)
        self.assertIn("_ensure_admin_site_access(admin, site_id)", routes_source)
        self.assertIn("ext_camping", fields)
        self.assertIn("ext_activity", fields)
        self.assertIn("ext_rental", fields)
        self.assertIn("ext_shop", fields)

    def test_product_service_update_upserts_extensions_and_syncs_skus(self):
        from services import product_service

        source = inspect.getsource(product_service.update_product)
        self.assertIn("_upsert_product_extension", source)
        self.assertIn("_sync_product_skus", source)

        helper_source = inspect.getsource(product_service)
        self.assertIn("async def _upsert_product_extension", helper_source)
        self.assertIn("async def _sync_product_skus", helper_source)
        self.assertIn("sku.is_deleted = True", helper_source)
        self.assertIn("ProductExtCamping", helper_source)
        self.assertIn("ProductExtActivity", helper_source)
        self.assertIn("ProductExtRental", helper_source)
        self.assertIn("ProductExtShop", helper_source)

    def test_product_type_switch_clears_stale_extension_objects(self):
        async def run_case():
            from services import product_service

            db = SimpleNamespace(add=lambda obj: setattr(db, "added", obj), delete=AsyncMock())
            old_rental_ext = SimpleNamespace(product_id=7, deposit_amount=Decimal("99.00"))
            product = SimpleNamespace(
                id=7,
                type="shop",
                ext_camping=None,
                ext_activity=None,
                ext_rental=old_rental_ext,
                ext_shop=None,
            )

            await product_service._upsert_product_extension(
                db,
                product,
                {
                    "ext_camping": None,
                    "ext_activity": None,
                    "ext_rental": None,
                    "ext_shop": {"shop_type": "drink"},
                },
            )

            db.delete.assert_awaited_once_with(old_rental_ext)
            self.assertIsNone(product.ext_rental)
            self.assertIsNotNone(product.ext_shop)

        asyncio.run(run_case())

    async def _obsolete_async_product_type_switch_test(self):
        from services import product_service

        db = SimpleNamespace(delete=AsyncMock())
        product = SimpleNamespace(
            id=7,
            type="shop",
            ext_camping=None,
            ext_activity=None,
            ext_rental=SimpleNamespace(product_id=7, deposit_amount=Decimal("99.00")),
            ext_shop=None,
        )

        await product_service._upsert_product_extension(
            db,
            product,
            {
                "ext_camping": None,
                "ext_activity": None,
                "ext_rental": None,
                "ext_shop": {"shop_type": "drink"},
            },
        )

        db.delete.assert_awaited_once_with(product.ext_rental)
        self.assertIsNone(product.ext_rental)
        self.assertIsNotNone(product.ext_shop)


class V18WechatPaymentHardeningContractTest(unittest.TestCase):
    def test_payment_notification_validates_site_app_mchid_and_amount(self):
        from services import order_service

        source = inspect.getsource(order_service.handle_wechat_payment_notification)
        self.assertIn("_validate_wechat_payment_transaction", source)
        helper_source = inspect.getsource(order_service._validate_wechat_payment_transaction)
        self.assertIn("order.site_id", helper_source)
        self.assertIn("appid", helper_source)
        self.assertIn("mchid", helper_source)
        self.assertIn("amount", helper_source)

    def test_mark_order_paid_allows_trusted_wechat_notification_to_reconcile_expired_pending_order(self):
        from services import order_service

        source = inspect.getsource(order_service.handle_wechat_payment_notification)
        self.assertIn("allow_expired=True", source)

    def test_cart_quote_reuses_order_service_quote_and_returns_real_stock(self):
        from routers import cart

        list_source = inspect.getsource(cart.list_cart_items)
        quote_source = inspect.getsource(cart.quote_cart)
        self.assertIn('"stock": stock', list_source)
        self.assertIn("stock = sku.stock", list_source)
        self.assertIn("order_service.quote_order", quote_source)
        self.assertIn("disclaimer_signed: bool = Body(default=False", quote_source)
        self.assertIn('/quote"', quote_source)


class V18EnterpriseWechatRobotContractTest(unittest.TestCase):
    def test_enterprise_wechat_robot_models_are_registered_in_metadata(self):
        import models  # noqa: F401
        from models.base import Base

        expected_tables = {
            "enterprise_wechat_robot_config",
            "enterprise_wechat_robot_message_log",
        }

        self.assertTrue(expected_tables.issubset(set(Base.metadata.tables)))

    def test_signed_webhook_url_uses_enterprise_wechat_robot_secret(self):
        from services.enterprise_wechat_robot_service import build_signed_webhook_url

        url = build_signed_webhook_url(
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=robot-key",
            secret="secret",
            timestamp_ms="1700000000000",
        )

        self.assertEqual(
            url,
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
            "?key=robot-key&timestamp=1700000000000"
            "&sign=OuzzJR5%2BxZ4%2FEYwqtNt6sMYZQMTa%2FHEGvc9miJe7XzY%3D",
        )

    def test_robot_text_payload_has_enterprise_wechat_shape(self):
        from services.enterprise_wechat_robot_service import build_text_payload

        payload = build_text_payload("库存不足，请及时处理", mentioned_mobile_list=["13800000000"])

        self.assertEqual(payload["msgtype"], "text")
        self.assertEqual(payload["text"]["content"], "库存不足，请及时处理")
        self.assertEqual(payload["text"]["mentioned_mobile_list"], ["13800000000"])

    def test_webhook_url_must_be_enterprise_wechat_group_robot(self):
        from services.enterprise_wechat_robot_service import validate_enterprise_wechat_webhook_url

        validate_enterprise_wechat_webhook_url(
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=robot-key"
        )

        invalid_urls = [
            "http://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=robot-key",
            "https://example.com/cgi-bin/webhook/send?key=robot-key",
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/other?key=robot-key",
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_enterprise_wechat_webhook_url(url)


class V18OrderQuoteContractTest(unittest.TestCase):
    def test_order_quote_schema_accepts_same_payload_as_order_create(self):
        from schemas.order import OrderQuoteRequest

        request = OrderQuoteRequest.model_validate(
            {
                "items": [
                    {
                        "product_id": 12,
                        "sku_id": 34,
                        "quantity": 2,
                        "dates": ["2026-07-01", "2026-07-02"],
                    }
                ],
                "disclaimer_signed": True,
            }
        )

        self.assertEqual(request.items[0].product_id, 12)
        self.assertEqual(request.items[0].sku_id, 34)
        self.assertEqual(request.items[0].quantity, 2)
        self.assertEqual(len(request.items[0].dates), 2)

    def test_shared_inventory_quote_helpers_use_explicit_pool_binding(self):
        from types import SimpleNamespace
        from services.inventory_pool_service import resolve_bound_inventory_pool, validate_pool_availability

        pools = {
            1: SimpleNamespace(id=1, available=3, status="active"),
        }
        bindings = [
            SimpleNamespace(
                inventory_pool_id=1,
                status="active",
                product_id=8,
                sku_id=None,
                activity_session_id=None,
                rental_asset_id=None,
                priority=100,
            )
        ]

        pool = resolve_bound_inventory_pool(
            bindings,
            pools=pools,
            product_id=8,
            sku_id=None,
            activity_session_id=None,
            rental_asset_id=None,
        )

        self.assertIsNotNone(pool)
        self.assertEqual(pool.id, 1)
        validate_pool_availability(pool, required_quantity=3)
        with self.assertRaises(ValueError):
            validate_pool_availability(pool, required_quantity=4)

    def test_price_calendar_uses_shared_inventory_pool_when_bound(self):
        from services import product_service

        source = inspect.getsource(product_service.get_price_calendar)
        self.assertIn("get_bound_inventory_pool", source)
        self.assertIn("inventory_pool", source)

    def test_price_calendar_supports_sku_level_inventory_pool_binding(self):
        from routers import products
        from services import product_service

        route_signature = inspect.signature(products.get_price_calendar)
        service_signature = inspect.signature(product_service.get_price_calendar)
        service_source = inspect.getsource(product_service.get_price_calendar)

        self.assertIn("sku_id", route_signature.parameters)
        self.assertIn("sku_id", service_signature.parameters)
        self.assertIn("sku_id=sku_id", service_source)
        self.assertIn("sku_price", service_source)
        self.assertLess(
            service_source.index("sku_price"),
            service_source.index("custom_date_rules"),
            "SKU 价格应优先于价格日历日期规则",
        )


class V18ProductDetailContractTest(unittest.TestCase):
    def test_product_detail_schema_declares_stock_for_miniapp_contract(self):
        from schemas.product import ProductDetail

        self.assertIn("stock", ProductDetail.model_fields)

    def test_product_detail_route_serializes_computed_stock(self):
        from routers import products

        source = inspect.getsource(products.get_product_detail)

        self.assertIn("resolve_product_detail_stock", source)
        self.assertIn('"stock"', source)


class V18MapAnalyticsContractTest(unittest.TestCase):
    def test_camp_map_zone_supports_link_and_click_count(self):
        from models.camp_map import CampMapZone
        from schemas.camp_map import CampMapZoneCreate, CampMapZoneResponse

        columns = set(CampMapZone.__table__.columns.keys())
        self.assertTrue(
            {
                "link_type",
                "link_target",
                "link_label",
                "click_count",
            }.issubset(columns)
        )
        self.assertIn("link_type", CampMapZoneCreate.model_fields)
        self.assertIn("link_target", CampMapZoneCreate.model_fields)
        self.assertIn("click_count", CampMapZoneResponse.model_fields)
        zone = CampMapZoneCreate.model_validate(
            {
                "zone_name": "湖畔区",
                "coordinates": {"x": 10, "y": 12, "width": 20, "height": 16},
                "link_type": "cms",
                "link_target": "lake",
            }
        )
        self.assertEqual(zone.coordinates.x, 10)
        self.assertEqual(zone.link_type, "cms")

        legacy_zone = SimpleNamespace(
            id=1,
            camp_map_id=2,
            zone_name="老数据区域",
            zone_code=None,
            coordinates=[
                {"x": 10, "y": 20},
                {"x": 30, "y": 20},
                {"x": 30, "y": 45},
                {"x": 10, "y": 45},
            ],
            product_ids=[],
            description=None,
            sort_order=0,
            link_type=None,
            link_target=None,
            link_label=None,
            click_count=0,
        )
        response = CampMapZoneResponse.model_validate(legacy_zone)
        self.assertEqual(response.coordinates.x, 10)
        self.assertEqual(response.coordinates.y, 20)
        self.assertEqual(response.coordinates.width, 20)
        self.assertEqual(response.coordinates.height, 25)

    def test_page_view_stat_model_and_routes_are_registered(self):
        import models  # noqa: F401
        from main import app
        from models.base import Base
        from models.camp_map import PageViewStat

        self.assertIn("page_view_stat", Base.metadata.tables)
        self.assertIn("page_key", PageViewStat.__table__.columns)
        paths = {route.path for route in app.routes}
        self.assertTrue(
            {
                "/api/v1/analytics/page-view",
                "/api/v1/camp-maps/zones/{zone_id}/click",
                "/api/v1/admin/analytics/page-views",
            }.issubset(paths)
        )

    def test_camp_map_service_tracks_zone_clicks_and_page_views(self):
        from services import camp_map_service

        self.assertTrue(hasattr(camp_map_service, "record_zone_click"))
        self.assertTrue(hasattr(camp_map_service, "record_page_view"))
        self.assertTrue(hasattr(camp_map_service, "list_page_view_stats"))
        self.assertTrue(hasattr(camp_map_service, "summarize_page_view_stats"))

        zone_click_source = inspect.getsource(camp_map_service.record_zone_click)
        page_view_source = inspect.getsource(camp_map_service.record_page_view)
        availability_source = inspect.getsource(camp_map_service.get_zone_availability)

        self.assertIn("update(CampMapZone)", zone_click_source)
        self.assertIn("CampMapZone.click_count + 1", zone_click_source)
        self.assertIn("pg_insert(PageViewStat)", page_view_source)
        self.assertIn("on_conflict_do_update", page_view_source)
        self.assertIn("Inventory.site_id == site_id", availability_source)

    def test_admin_camp_map_routes_use_request_site_scope(self):
        from routers import camp_maps

        admin_handlers = [
            camp_maps.list_camp_maps_admin,
            camp_maps.create_camp_map,
            camp_maps.update_camp_map,
            camp_maps.delete_camp_map,
            camp_maps.create_camp_map_zone,
            camp_maps.update_camp_map_zone,
            camp_maps.delete_camp_map_zone,
            camp_maps.list_page_view_stats,
        ]
        for handler in admin_handlers:
            source = inspect.getsource(handler)
            self.assertIn("request: Request", source, handler.__name__)
            self.assertIn("site_id = get_site_id(request)", source, handler.__name__)


class V18PhoneLoginContractTest(unittest.TestCase):
    def test_phone_login_route_uses_real_wechat_phone_service(self):
        from routers import auth
        from services import auth_service

        route_source = inspect.getsource(auth.phone_login)
        service_source = inspect.getsource(auth_service.phone_login)
        phone_api_source = inspect.getsource(auth_service._get_phone_number)

        self.assertIn("auth_service.phone_login", route_source)
        self.assertNotIn("TODO", route_source)
        self.assertIn("_get_phone_number", service_source)
        self.assertIn("user.phone = phone_number", service_source)
        self.assertIn("/wxa/business/getuserphonenumber", phone_api_source)
        self.assertIn("phone_info", phone_api_source)


class V18OrderInventoryStateMachineTest(unittest.IsolatedAsyncioTestCase):
    async def test_late_wechat_payment_notification_does_not_pay_cancelled_order(self):
        from services import order_service

        db = SimpleNamespace(flush=AsyncMock())
        order = SimpleNamespace(
            id=1001,
            status="cancelled",
            payment_status="unpaid",
            expire_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            items=[],
        )

        with self.assertRaises(Exception):
            await order_service.mark_order_paid(db, order, payment_no="wx-late")

        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.payment_status, "unpaid")

    def test_order_items_are_not_duplicated_by_identity_ids(self):
        from services import order_service

        source = inspect.getsource(order_service.create_order)

        self.assertNotIn("for identity_id in identity_ids", source)

    async def test_partial_refund_releases_only_refund_item_quantity(self):
        from services import refund_service

        db = SimpleNamespace(flush=AsyncMock())
        order_item = SimpleNamespace(id=10, quantity=5)
        refund_item = SimpleNamespace(
            order_item_id=10,
            quantity=2,
            release_inventory=True,
        )
        refund = SimpleNamespace(
            id=99,
            order_id=1,
            site_id=1,
            release_inventory=True,
            order_action="cancel_order",
            inventory_released=False,
            items=[refund_item],
        )
        order = SimpleNamespace(id=1, items=[order_item])

        with patch.object(refund_service.order_service, "_refund_order_item_inventory", AsyncMock()) as release:
            await refund_service._release_refund_record_inventory(db, refund, order=order)

        release.assert_awaited_once_with(db, order_item, 1, quantity=2)
        self.assertTrue(refund.inventory_released)

    async def test_late_wechat_success_relocks_released_plain_inventory_before_confirm(self):
        from services import order_service

        db = SimpleNamespace(flush=AsyncMock())
        item = SimpleNamespace(
            product_id=11,
            sku_id=3,
            date=date(2026, 7, 1),
            time_slot="am",
            quantity=2,
            inventory_pool_id=None,
        )
        order = SimpleNamespace(
            id=1002,
            status="cancelled",
            payment_status="unpaid",
            expire_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            items=[item],
            remark="",
            order_type="daily_camping",
        )

        with (
            patch.object(order_service.inventory_service, "lock_inventory", AsyncMock()) as lock_inventory,
            patch.object(order_service.inventory_service, "confirm_sell", AsyncMock()) as confirm_sell,
            patch.object(order_service.settlement_service, "record_payment_pending_income", AsyncMock()),
            patch.object(order_service, "_generate_tickets", AsyncMock()),
        ):
            await order_service.mark_order_paid(
                db,
                order,
                payment_no="wx-late",
                allow_expired=True,
            )

        lock_inventory.assert_awaited_once_with(db, 11, date(2026, 7, 1), 2, 1002, 3, "am")
        confirm_sell.assert_awaited_once_with(db, 11, date(2026, 7, 1), 2, 1002, 3, "am")
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")

    async def test_late_wechat_success_relocks_released_inventory_pool_before_confirm(self):
        from services import order_service

        db = SimpleNamespace(flush=AsyncMock())
        item = SimpleNamespace(
            product_id=11,
            sku_id=3,
            date=date(2026, 7, 1),
            time_slot="am",
            quantity=2,
            inventory_pool_id=88,
        )
        order = SimpleNamespace(
            id=1003,
            status="cancelled",
            payment_status="unpaid",
            expire_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            items=[item],
            remark="",
            order_type="daily_camping",
        )

        with (
            patch.object(order_service.inventory_pool_service, "lock_pool_inventory", AsyncMock()) as lock_pool,
            patch.object(order_service.inventory_pool_service, "confirm_pool_sell", AsyncMock()) as confirm_pool,
            patch.object(order_service.settlement_service, "record_payment_pending_income", AsyncMock()),
            patch.object(order_service, "_generate_tickets", AsyncMock()),
        ):
            await order_service.mark_order_paid(
                db,
                order,
                payment_no="wx-late",
                allow_expired=True,
            )

        lock_pool.assert_awaited_once_with(db, pool_id=88, quantity=2)
        confirm_pool.assert_awaited_once_with(db, pool_id=88, quantity=2)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")


class V18AdminRouteContractTest(unittest.TestCase):
    def test_admin_product_and_order_routes_check_admin_site_access(self):
        from routers import orders, products

        products_source = inspect.getsource(products)
        orders_source = inspect.getsource(orders)
        self.assertIn("def _ensure_admin_site_access", products_source)
        self.assertGreaterEqual(products_source.count("_ensure_admin_site_access(admin, site_id)"), 6)
        self.assertIn("def _ensure_admin_site_access", orders_source)
        self.assertGreaterEqual(orders_source.count("_ensure_admin_site_access(admin, site_id)"), 5)

    def test_codepay_unknown_state_does_not_raise_and_rollback_local_order(self):
        from services import order_service

        source = inspect.getsource(order_service.charge_temporary_order_by_auth_code)
        self.assertIn('trade_state": "UNKNOWN"', source)
        self.assertIn('"requires_query": True', source)
        unknown_branch = source.split("except wechat_pay_service.WechatPayError", 1)[1]
        unknown_branch = unknown_branch.split("trade_state = result.get", 1)[0]
        self.assertNotIn("raise HTTPException", unknown_branch)
        self.assertIn("return order, unknown_result", unknown_branch)

    def test_temporary_codepay_query_route_and_service_exist(self):
        from routers import orders
        from services import order_service

        service_source = inspect.getsource(order_service.query_temporary_codepay_result)
        admin_source = inspect.getsource(orders.admin_query_temporary_codepay)
        staff_source = inspect.getsource(orders.staff_query_temporary_codepay)

        self.assertIn("query_codepay_transaction", service_source)
        self.assertIn("mark_order_paid", service_source)
        self.assertIn("allow_expired=True", service_source)
        self.assertIn(".with_for_update()", service_source)
        self.assertIn("_ensure_admin_site_access(admin, site_id)", admin_source)
        self.assertIn('operator_source="admin"', admin_source)
        self.assertIn("operator_source=staff.source", staff_source)
        self.assertIn("requires_query", admin_source)
        self.assertIn("requires_query", staff_source)

    def test_wechat_success_notification_locks_order_and_can_reconcile_auto_cancelled_order(self):
        from services import order_service

        notify_source = inspect.getsource(order_service.handle_wechat_payment_notification)
        paid_source = inspect.getsource(order_service.mark_order_paid)
        self.assertIn(".with_for_update()", notify_source)
        self.assertIn('order.status == "cancelled"', paid_source)
        self.assertIn("allow_expired", paid_source)
        self.assertIn("payment_status == \"unpaid\"", paid_source)

    def test_v18_admin_routes_are_registered(self):
        from main import app

        paths = {route.path for route in app.routes}

        expected_paths = {
            "/api/v1/admin/inventory/calendar",
            "/api/v1/admin/inventory/batch-upsert",
            "/api/v1/admin/inventory-pools",
            "/api/v1/admin/inventory-pools/{pool_id}",
            "/api/v1/admin/inventory-pools/{pool_id}/adjust",
            "/api/v1/admin/inventory-pools/{pool_id}/bindings",
            "/api/v1/admin/inventory-pool-bindings/{binding_id}",
            "/api/v1/admin/enterprise-wechat/robots",
            "/api/v1/admin/enterprise-wechat/robots/{robot_id}",
            "/api/v1/admin/enterprise-wechat/robots/{robot_id}/test-send",
            "/api/v1/admin/enterprise-wechat/robots/{robot_id}/logs",
            "/api/v1/orders/quote",
            "/api/v1/admin/orders/temporary/{session_id}/query-codepay",
            "/api/v1/staff/orders/temporary/{session_id}/query-codepay",
        }

        self.assertTrue(expected_paths.issubset(paths))

    def test_inventory_calendar_routes_are_super_admin_and_high_risk_for_writes(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router)

        self.assertRegex(source, r"async def get_inventory_calendar[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def get_inventory_calendar[\s\S]*time_slot")
        self.assertRegex(source, r"async def batch_upsert_inventory_calendar[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def batch_upsert_inventory_calendar[\s\S]*?_require_high_risk_confirm")
        self.assertRegex(source, r"async def adjust_inventory_pool[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def adjust_inventory_pool[\s\S]*?_require_high_risk_confirm")

    def test_inventory_batch_service_uses_site_scope_and_rejects_pool_targets(self):
        from services import inventory_calendar_service

        source = inspect.getsource(inventory_calendar_service.batch_upsert_inventory)

        self.assertIn("site_id", source)
        self.assertIn("ensure_targets_not_pool_bound", source)
        self.assertIn("recompute_available", source)
        self.assertIn("IntegrityError", source)
        self.assertIn("库存日历已被并发请求更新", source)
        self.assertNotIn("max(0", source)

    def test_inventory_pool_update_route_rejects_direct_quantity_state_writes(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router.update_inventory_pool)

        self.assertIn("forbidden_quantity_fields", source)
        self.assertIn("raise HTTPException", source)
        self.assertNotIn("pool.locked = locked", source)
        self.assertNotIn("pool.sold = sold", source)
        self.assertNotIn("pool.available = available", source)

    def test_inventory_unique_index_migration_is_chained_after_v18_head(self):
        migration = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("alembic", "versions", "c3d4e5f6a7b8_v1_8_add_inventory_calendar_unique_index.py")
        )

        self.assertTrue(migration.exists())
        source = migration.read_text(encoding="utf-8")
        self.assertIn("down_revision = 'b2c3d4e5f6a7'", source)
        self.assertIn("uq_inventory_site_product_sku_date_slot_active", source)
        self.assertIn("is_deleted = false", source)
        self.assertIn("_assert_no_duplicate_inventory_rows", source)
        self.assertIn("HAVING COUNT(*) > 1", source)
        self.assertIn("请先合并或软删除重复库存", source)

    def test_inventory_pool_list_accepts_keyword_filter(self):
        from routers.admin import list_inventory_pools

        signature = inspect.signature(list_inventory_pools)

        self.assertIn("keyword", signature.parameters)

    def test_inventory_pool_admin_routes_require_super_admin(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router)
        self.assertRegex(source, r"async def list_inventory_pools[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def create_inventory_pool[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def update_inventory_pool[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def list_inventory_pool_bindings[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def create_inventory_pool_binding[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def update_inventory_pool_binding[\s\S]*?_ensure_super_admin\(admin\)")

    def test_enterprise_wechat_admin_routes_require_super_admin(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router)
        self.assertRegex(source, r"async def list_enterprise_wechat_robots[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def create_enterprise_wechat_robot[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def update_enterprise_wechat_robot[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def test_send_enterprise_wechat_robot[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def list_enterprise_wechat_robot_logs[\s\S]*?_ensure_super_admin\(admin\)")

    def test_enterprise_wechat_log_serializer_redacts_sensitive_payload(self):
        from routers import admin as admin_router

        raw = {
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc",
            "text": {
                "mentioned_mobile_list": ["13800000000"],
            },
        }

        redacted = admin_router._redact_enterprise_wechat_log_value(raw)

        self.assertEqual(redacted["webhook_url"], "***")
        self.assertEqual(redacted["text"]["mentioned_mobile_list"], ["138****0000"])

    def test_enterprise_wechat_error_message_is_redacted(self):
        from routers import admin as admin_router

        message = (
            "请求失败 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?"
            "key=robot-key&timestamp=1700000000000&sign=abc 13800000000"
        )

        redacted = admin_router._redact_enterprise_wechat_log_value(message)

        self.assertNotIn("robot-key", redacted)
        self.assertNotIn("sign=abc", redacted)
        self.assertNotIn("13800000000", redacted)

    def test_legacy_refund_admin_routes_are_super_admin_and_use_refund_service(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router)

        self.assertRegex(source, r"async def approve_order_refund[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def partial_refund[\s\S]*?_ensure_super_admin\(admin\)")
        self.assertRegex(source, r"async def approve_order_refund[\s\S]*?refund_service\.")
        self.assertRegex(source, r"async def partial_refund[\s\S]*?refund_service\.")
        self.assertNotRegex(source, r"async def approve_order_refund[\s\S]*?order\.status = \"refunded\"")
        self.assertNotRegex(source, r"async def partial_refund[\s\S]*?order\.status = \"partial_refunded\"")

    def test_legacy_refund_admin_approval_reuses_existing_pending_refund(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router.approve_order_refund)

        self.assertIn("find_pending_refund_for_order", source)
        self.assertIn("if refund is None", source)
        self.assertIn("refund_service.approve_refund", source)

    def test_refund_admin_queue_filters_refund_record_status(self):
        from routers import refunds
        from services import refund_service

        route_source = inspect.getsource(refunds.list_refunds)
        service_source = inspect.getsource(refund_service.list_refunds)

        self.assertIn("status: str | None = None", route_source)
        self.assertIn("refund_status=status", route_source)
        self.assertIn("refund_status: Optional[str] = None", service_source)
        self.assertIn("RefundRecord.status == refund_status", service_source)

    def test_refund_admin_routes_enforce_site_and_role_guard(self):
        from routers import refunds

        source = inspect.getsource(refunds)
        self.assertIn("def _ensure_refund_admin_access", source)
        self.assertIn("def _ensure_super_admin", source)

        for route in [
            refunds.create_refund,
            refunds.list_order_refunds,
            refunds.list_refunds,
            refunds.get_refund_detail,
            refunds.approve_refund,
            refunds.reject_refund,
        ]:
            self.assertIn("_ensure_refund_admin_access(admin, site_id)", inspect.getsource(route))

        self.assertIn("_ensure_super_admin(admin)", inspect.getsource(refunds.approve_refund))
        self.assertIn("_ensure_super_admin(admin)", inspect.getsource(refunds.reject_refund))

    def test_admin_order_refund_approve_route_uses_refund_service_state_machine(self):
        from routers import orders

        source = inspect.getsource(orders.approve_refund)

        self.assertIn("find_pending_refund_for_order", source)
        self.assertIn("refund_service.approve_refund", source)
        self.assertIn("role_code != \"super_admin\"", source)
        self.assertNotIn("order_service.approve_refund", source)

    def test_high_risk_confirm_routes_reject_placeholder_success(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router.verify_confirm_code)
        password_source = inspect.getsource(admin_router.verify_operation_password)

        self.assertNotIn("code 不为空即通过", source)
        self.assertIn("_ensure_super_admin(admin)", source)
        self.assertIn("操作密码未设置", source)
        self.assertIn("确认码错误", source)
        self.assertIn("operation_password_hash", password_source)
        self.assertIn("操作密码未设置", password_source)


class V18StaffTicketContractTest(unittest.TestCase):
    def test_staff_ticket_routes_are_registered(self):
        from main import app

        paths = {route.path for route in app.routes}

        self.assertTrue(
            {
                "/api/v1/staff/orders/today",
                "/api/v1/staff/tickets/pending",
                "/api/v1/staff/tickets/logs",
            }.issubset(paths)
        )

    def test_scan_ticket_writes_verification_log(self):
        from services import ticket_service

        source = inspect.getsource(ticket_service.scan_ticket)

        self.assertIn("_create_ticket_verify_log", source)
        self.assertIn("verify_result", source)

    def test_ticket_persists_qr_token_hash_instead_of_plain_token(self):
        from models.order import Ticket
        from services import order_service, ticket_service

        columns = set(Ticket.__table__.columns.keys())
        self.assertIn("qr_token_hash", columns)
        self.assertNotIn("qr_token", columns)

        generate_source = inspect.getsource(order_service._generate_tickets)
        refresh_source = inspect.getsource(ticket_service.refresh_qr_token)
        scan_source = inspect.getsource(ticket_service.scan_ticket)

        self.assertIn("_hash_qr_token", generate_source)
        self.assertIn("qr_token_hash=", generate_source)
        self.assertIn("ticket.qr_token_hash = _hash_qr_token(new_token)", refresh_source)
        self.assertIn("Ticket.qr_token_hash == qr_token_hash", scan_source)

    def test_ticket_customer_routes_require_site_scope(self):
        from routers import tickets
        from services import ticket_service

        detail_source = inspect.getsource(tickets.get_ticket_detail)
        refresh_source = inspect.getsource(tickets.refresh_qr_token)
        service_detail_signature = inspect.signature(ticket_service.get_ticket_detail)
        service_refresh_signature = inspect.signature(ticket_service.refresh_qr_token)

        self.assertIn("get_site_id", detail_source)
        self.assertIn("site_id=site_id", detail_source)
        self.assertIn("get_site_id", refresh_source)
        self.assertIn("site_id=site_id", refresh_source)
        self.assertIn("site_id", service_detail_signature.parameters)
        self.assertIn("site_id", service_refresh_signature.parameters)

    def test_invalid_ticket_scan_logs_to_staff_site(self):
        from services import ticket_service

        source = inspect.getsource(ticket_service.scan_ticket)
        helper_source = inspect.getsource(ticket_service._create_ticket_verify_log)
        verify_code_source = inspect.getsource(ticket_service.verify_code)

        self.assertIn("site_id=staff_site_id", source)
        self.assertIn("Ticket.site_id == staff_site_id", source)
        self.assertIn("with_for_update", source)
        self.assertIn("commit_immediately", helper_source)
        self.assertIn("async_session_factory", helper_source)
        self.assertIn('log_data["ticket_id"] = None', helper_source)
        self.assertIn('log_data["order_id"] = None', helper_source)
        self.assertIn('log_data["order_item_id"] = None', helper_source)
        self.assertIn("commit_immediately=True", source)
        self.assertIn("commit_immediately=True", verify_code_source)
        self.assertIn("with_for_update", verify_code_source)
        self.assertNotIn("员工无权核销其他营地票券", source)

    def test_sku_price_is_used_for_non_campsite_quote_and_order(self):
        from services import order_service

        source = inspect.getsource(order_service)
        create_source = inspect.getsource(order_service.create_order)
        quote_source = inspect.getsource(order_service.quote_order)
        resolve_price_signature = inspect.signature(order_service._resolve_price)
        resolve_price_source = inspect.getsource(order_service._resolve_price)

        self.assertIn("SKU", source)
        self.assertIn("_resolve_sku_price", source)
        self.assertIn("unit_price = await _resolve_sku_price", create_source)
        self.assertIn("unit_price = await _resolve_sku_price", quote_source)
        self.assertIn("sku_id", resolve_price_signature.parameters)
        self.assertIn("return await _resolve_sku_price", resolve_price_source)
        self.assertLess(
            resolve_price_source.index("return await _resolve_sku_price"),
            resolve_price_source.index("select(PricingRule)"),
            "日期商品选中 SKU 后应优先使用 SKU 价，再考虑日期规则",
        )
        self.assertIn("sku_id=sku_id", create_source)
        self.assertIn("sku_id=sku_id", quote_source)


if __name__ == "__main__":
    unittest.main()
