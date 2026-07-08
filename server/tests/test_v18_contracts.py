import asyncio
import unittest
import inspect
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch


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

    def test_product_editor_supports_product_private_sku_shared_inventory(self):
        from routers import cart
        from schemas.product import SKUCreate, SKUSchema, SKUUpdate
        from services import inventory_pool_service
        from services import product_service

        self.assertIn("inventory_mode", SKUCreate.model_fields)
        self.assertIn("inventory_mode", SKUUpdate.model_fields)
        self.assertIn("inventory_mode", SKUSchema.model_fields)
        self.assertIn("inventory_pool_id", SKUSchema.model_fields)
        self.assertIn("inventory_pool_available", SKUSchema.model_fields)
        sku_payload = SKUCreate(price=Decimal("10.00"), stock=5, spec_values="一大一小")
        self.assertIsNone(sku_payload.sku_code)
        self.assertEqual(sku_payload.spec_values, {"规格": "一大一小"})
        self.assertEqual(product_service.normalize_sku_inventory_mode(None), "independent")
        self.assertEqual(product_service.normalize_sku_inventory_mode("shared_product"), "shared_product")

        create_source = inspect.getsource(product_service.create_product)
        update_source = inspect.getsource(product_service.update_product)
        sync_source = inspect.getsource(product_service._sync_product_sku_inventory_pool)
        pool_source = inspect.getsource(product_service._get_or_create_product_sku_shared_pool)
        annotate_source = inspect.getsource(product_service.annotate_product_sku_inventory_modes)
        get_bound_source = inspect.getsource(inventory_pool_service.get_bound_inventory_pool)
        cart_list_source = inspect.getsource(cart.list_cart_items)
        stock_source = inspect.getsource(product_service.resolve_product_detail_stock)

        self.assertIn("inventory_mode", create_source)
        self.assertIn("_ensure_sku_code", create_source)
        self.assertIn("_normalize_sku_spec_values", create_source)
        self.assertIn("_sync_product_sku_inventory_pool", create_source)
        self.assertIn('set_committed_value(product, "skus"', create_source)
        self.assertLess(
            create_source.index('set_committed_value(product, "skus"'),
            create_source.index("await annotate_product_sku_inventory_modes(db, product)"),
            "创建商品后必须先显式填充 product.skus，避免 async 懒加载触发 MissingGreenlet",
        )
        self.assertIn("_sync_product_sku_inventory_pool", update_source)
        self.assertIn("_product_sku_shared_pool_code", pool_source)
        self.assertIn("InventoryPool.pool_code == _product_sku_shared_pool_code(product)", annotate_source)
        self.assertIn("inventory_pool_available", annotate_source)
        self.assertIn("InventoryPoolBinding.sku_id == sku_id", get_bound_source)
        self.assertNotIn("get_product_sku_shared_pool_code(site_id, product_id)", get_bound_source)
        self.assertIn("sku_pool_map", cart_list_source)
        self.assertIn("expected_pool_code_by_sku", cart_list_source)
        self.assertIn("InventoryPoolBinding.sku_id == sku_id", cart_list_source)
        self.assertIn("InventoryPool.pool_code == pool_code", cart_list_source)
        self.assertIn("stock = int(pool.available) if pool else int(sku.stock)", cart_list_source)
        self.assertIn("InventoryPoolBinding(", sync_source)
        self.assertIn("sku_id=sku.id", sync_source)
        self.assertIn("binding.status = \"inactive\"", sync_source)
        self.assertIn("InventoryPool.pool_code == _product_sku_shared_pool_code(product)", sync_source)
        self.assertNotIn("InventoryPoolBinding.product_id == product.id", sync_source)
        self.assertIn("counted_pool_ids", stock_source)

    def test_inventory_pool_resolution_prefers_sku_binding_over_product_binding(self):
        from services.inventory_pool_service import resolve_bound_inventory_pool

        pools = {
            1: SimpleNamespace(id=1, status="active", available=5),
            2: SimpleNamespace(id=2, status="active", available=9),
        }
        bindings = [
            SimpleNamespace(
                id=1,
                inventory_pool_id=2,
                status="active",
                product_id=8,
                sku_id=None,
                activity_session_id=None,
                rental_asset_id=None,
                priority=1,
            ),
            SimpleNamespace(
                id=2,
                inventory_pool_id=1,
                status="active",
                product_id=None,
                sku_id=18,
                activity_session_id=None,
                rental_asset_id=None,
                priority=100,
            ),
        ]

        pool = resolve_bound_inventory_pool(
            bindings,
            pools=pools,
            product_id=8,
            sku_id=18,
        )

        self.assertEqual(pool.id, 1)

    def test_product_list_supports_manual_ids_for_cms_product_list(self):
        from routers import products
        from schemas.product import ProductSearchParams
        from services import product_service

        self.assertIn("ids", ProductSearchParams.model_fields)
        route_source = inspect.getsource(products.list_products)
        service_source = inspect.getsource(product_service.list_products)

        self.assertIn("_parse_product_ids(params.ids)", route_source)
        self.assertIn("product_ids=params_product_ids", route_source)
        self.assertIn("product_ids", inspect.signature(product_service.list_products).parameters)
        self.assertIn("Product.id.in_(product_ids)", service_source)

    def test_cloud_files_backend_exports_and_archives_sources(self):
        from routers import cms
        from services import cms_service, qrcode_service

        route_source = inspect.getsource(cms.export_campsite_info_asset)
        cms_source = inspect.getsource(cms_service.export_campsite_info_asset)
        register_source = inspect.getsource(cms_service.register_existing_asset)
        qrcode_source = inspect.getsource(qrcode_service.create_or_reuse_qrcode)
        regenerate_source = inspect.getsource(qrcode_service.regenerate_qrcode)

        self.assertIn("/admin/cms/assets/export/campsites", route_source)
        self.assertIn("file_type=\"export\"", cms_source)
        self.assertIn("/images/exports/", cms_source)
        self.assertIn("daily_camping", cms_source)
        self.assertIn("event_camping", cms_source)
        self.assertIn("register_existing_asset", qrcode_source)
        self.assertIn("register_existing_asset", regenerate_source)
        self.assertIn("file_type=\"qrcode\"", qrcode_source)
        self.assertIn("CmsAsset.file_url == file_url", register_source)

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

    def test_cart_sku_static_stock_checks_skip_shared_inventory_pool(self):
        from routers import cart

        add_source = inspect.getsource(cart.add_cart_item)
        checkout_source = inspect.getsource(cart.checkout)
        update_source = inspect.getsource(cart.update_cart_item)

        self.assertTrue(hasattr(cart, "_validate_cart_sku_stock"))
        helper_source = inspect.getsource(cart._validate_cart_sku_stock)
        self.assertIn("inventory_pool_service.get_bound_inventory_pool", helper_source)
        self.assertIn("inventory_pool_service.validate_pool_availability", helper_source)
        self.assertIn("if pool:", helper_source)
        self.assertIn("return", helper_source)

        self.assertIn("_validate_cart_sku_stock", add_source)
        self.assertIn("_validate_cart_sku_stock", checkout_source)
        self.assertIn("_validate_cart_sku_stock", update_source)
        self.assertNotIn("if sku.stock < quantity:", add_source)
        self.assertNotIn("if sku.stock < item.quantity:", checkout_source)
        self.assertNotIn("if sku and sku.stock < quantity:", update_source)

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
        self.assertIn("stock = int(pool.available) if pool else int(sku.stock)", list_source)
        self.assertIn('"shipping_required"', list_source)
        self.assertIn("product.ext_shop", list_source)
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

    def test_admin_product_create_reloads_detail_before_serializing(self):
        from routers import products

        module_source = inspect.getsource(products)
        source = inspect.getsource(products.create_product)

        self.assertIn("product_service.create_product", source)
        self.assertIn("_serialize_product_detail_after_write", module_source)
        self.assertIn("detail = await _serialize_product_detail_after_write(db, product.id)", source)
        self.assertNotIn("ProductDetail.model_validate(product)", source)
        self.assertNotIn("resolve_product_detail_stock(product)", source)
        self.assertIn("product_service.get_product_detail", module_source)
        self.assertIn("ProductDetail.model_validate(product_detail)", module_source)
        self.assertIn("resolve_product_detail_stock(product_detail)", module_source)

    def test_admin_product_update_reloads_detail_before_serializing(self):
        from routers import products

        module_source = inspect.getsource(products)
        source = inspect.getsource(products.update_product)

        self.assertIn("product_service.update_product", source)
        self.assertIn("_serialize_product_detail_after_write", module_source)
        self.assertIn("detail = await _serialize_product_detail_after_write(db, product.id)", source)
        self.assertNotIn("ProductDetail.model_validate(product)", source)
        self.assertNotIn("resolve_product_detail_stock(product)", source)
        self.assertIn("product_service.get_product_detail", module_source)
        self.assertIn("ProductDetail.model_validate(product_detail)", module_source)
        self.assertIn("resolve_product_detail_stock(product_detail)", module_source)

    def test_admin_product_update_serializes_reloaded_product_not_write_result(self):
        from routers import products

        db = object()
        request = SimpleNamespace(headers={"X-Site-Id": "1"})
        admin = SimpleNamespace(id=8, site_id=1, role=SimpleNamespace(role_code="admin"))
        body = SimpleNamespace(model_dump=lambda exclude_none=True: {"base_price": Decimal("9.90")})
        existing_product = SimpleNamespace(id=31, site_id=1)
        write_result_product = SimpleNamespace(id=31, site_id=1)
        reloaded_product = SimpleNamespace(id=31, site_id=1)
        detail_model = SimpleNamespace(model_copy=Mock(return_value={"id": 31, "stock": 7}))

        get_detail = AsyncMock(side_effect=[existing_product, reloaded_product])
        update_product = AsyncMock(return_value=write_result_product)

        with patch.object(products.product_service, "get_product_detail", get_detail), \
             patch.object(products.product_service, "update_product", update_product), \
             patch.object(products.product_service, "resolve_product_detail_stock", return_value=7) as resolve_stock, \
             patch.object(products.ProductDetail, "model_validate", return_value=detail_model) as model_validate:
            response = asyncio.run(
                products.update_product(
                    product_id=31,
                    body=body,
                    request=request,
                    db=db,
                    admin=admin,
                )
            )

        update_product.assert_awaited_once_with(
            db,
            31,
            {"base_price": Decimal("9.90")},
            operator_id=8,
        )
        self.assertEqual(get_detail.await_args_list[0].args, (db, 31))
        self.assertEqual(get_detail.await_args_list[1].args, (db, 31))
        model_validate.assert_called_once_with(reloaded_product)
        resolve_stock.assert_called_once_with(reloaded_product)
        detail_model.model_copy.assert_called_once_with(update={"stock": 7})
        self.assertEqual(response.data, {"id": 31, "stock": 7})


class AsyncOrmWriteSerializationContractTest(unittest.TestCase):
    def test_bundle_admin_writes_reload_config_before_serializing(self):
        from routers import bundles

        module_source = inspect.getsource(bundles)
        self.assertIn("_serialize_bundle_config_after_write", module_source)
        self.assertIn("bundle_service.get_bundle_config", module_source)

        for route in [bundles.create_bundle_config, bundles.update_bundle_config]:
            with self.subTest(route=route.__name__):
                source = inspect.getsource(route)
                self.assertIn("_serialize_bundle_config_after_write", source)
                self.assertNotIn("BundleConfigResponse.model_validate(config)", source)

    def test_camp_map_admin_writes_reload_before_serializing(self):
        from routers import camp_maps

        module_source = inspect.getsource(camp_maps)
        self.assertIn("_serialize_camp_map_after_write", module_source)
        self.assertIn("_serialize_mini_game_after_write", module_source)
        self.assertIn("camp_map_service.get_camp_map", module_source)
        self.assertIn("game_service.get_mini_game", module_source)

        expectations = [
            (camp_maps.create_camp_map, "CampMapResponse.model_validate(camp_map)"),
            (camp_maps.update_camp_map, "CampMapResponse.model_validate(camp_map)"),
            (camp_maps.create_game, "MiniGameResponse.model_validate(game)"),
            (camp_maps.update_game, "MiniGameResponse.model_validate(game)"),
        ]
        for route, unsafe_call in expectations:
            with self.subTest(route=route.__name__):
                source = inspect.getsource(route)
                self.assertIn("_serialize_", source)
                self.assertNotIn(unsafe_call, source)

    def test_performance_calculate_reloads_records_with_details_before_serializing(self):
        from routers import performance
        from services import performance_service

        route_source = inspect.getsource(performance.calculate_performance)
        service_source = inspect.getsource(performance_service)

        self.assertIn("get_performance_records_by_ids", service_source)
        self.assertIn("record_ids = [record.id for record in records]", route_source)
        self.assertIn("get_performance_records_by_ids", route_source)
        self.assertNotIn("PerformanceRecordResponse.model_validate(r) for r in records", route_source)

    def test_simple_orm_write_services_refresh_returned_models_before_serializing(self):
        from services import (
            expense_service,
            finance_service,
            member_service,
            order_export_service,
            qrcode_service,
            refund_service,
        )

        expectations = [
            (expense_service.create_expense_request, "await db.refresh(expense)"),
            (expense_service.approve_expense, "await db.refresh(expense)"),
            (expense_service.mark_expense_paid, "await db.refresh(expense)"),
            (finance_service.withdraw, "await db.refresh(tx)"),
            (finance_service.return_deposit, "await db.refresh(deposit)"),
            (member_service.activate_times_card, "await db.refresh(times_card)"),
            (qrcode_service.update_qrcode_status, "await db.refresh(qrcode)"),
            (qrcode_service.regenerate_qrcode, "await db.refresh(qrcode)"),
            (refund_service.create_refund_record, "await db.refresh(refund)"),
            (refund_service.approve_refund, "await db.refresh(refund)"),
            (refund_service.reject_refund, "await db.refresh(refund)"),
            (order_export_service.create_order_export_task, "await db.refresh(task)"),
        ]

        for func, expected in expectations:
            with self.subTest(func=func.__name__):
                source = inspect.getsource(func)
                self.assertIn(expected, source)

    def test_user_write_routes_refresh_before_serializing(self):
        from routers import users

        expectations = [
            (users.update_user_info, "await db.refresh(user)"),
            (users.create_identity, "await db.refresh(identity)"),
            (users.update_identity, "await db.refresh(identity)"),
            (users.create_address, "await db.refresh(address)"),
            (users.update_address, "await db.refresh(address)"),
        ]

        for route, expected in expectations:
            with self.subTest(route=route.__name__):
                source = inspect.getsource(route)
                self.assertIn(expected, source)


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

    def test_admin_cms_and_qrcode_routes_check_admin_site_access(self):
        from fastapi import HTTPException
        from routers import cms, qrcodes

        blocked_admin = SimpleNamespace(site_id=1, role=SimpleNamespace(role_code="admin"))
        super_admin = SimpleNamespace(site_id=1, role=SimpleNamespace(role_code="super_admin"))

        for module in (cms, qrcodes):
            module._ensure_admin_site_access(super_admin, 2)
            module._ensure_admin_site_access(blocked_admin, 1)
            with self.subTest(module=module.__name__):
                with self.assertRaises(HTTPException):
                    module._ensure_admin_site_access(blocked_admin, 2)

        cms_source = inspect.getsource(cms)
        qrcode_source = inspect.getsource(qrcodes)
        self.assertIn("def _ensure_admin_site_access", cms_source)
        self.assertGreaterEqual(cms_source.count("_ensure_admin_site_access(admin, site_id)"), 15)
        self.assertIn("def _ensure_admin_site_access", qrcode_source)
        self.assertGreaterEqual(qrcode_source.count("_ensure_admin_site_access(admin, site_id)"), 6)

    def test_admin_cms_lock_and_force_delete_use_site_safe_checks(self):
        from routers import cms

        acquire_source = inspect.getsource(cms.acquire_lock)
        release_source = inspect.getsource(cms.release_lock)
        delete_source = inspect.getsource(cms.delete_asset)

        self.assertIn("cms_service.get_page", acquire_source)
        self.assertIn("CMS_PAGE_NOT_FOUND", acquire_source)
        self.assertIn("cms_service.get_page", release_source)
        self.assertIn("CMS_PAGE_NOT_FOUND", release_source)
        self.assertIn('_get_admin_role_code(admin) != "super_admin"', delete_source)

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

    def test_legacy_admin_order_detail_reuses_order_service_schema(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router.admin_get_order_detail)

        self.assertIn("_ensure_admin_site_access(admin, site_id)", source)
        self.assertIn("order_service.get_order_detail", source)
        self.assertIn("OrderResponse.model_validate(order)", source)
        self.assertNotIn("item.subtotal", source)
        self.assertNotIn("item.use_date", source)

    def test_qrcode_download_returns_transparent_png_copy(self):
        from routers import qrcodes
        from services import qrcode_service

        route_source = inspect.getsource(qrcodes.download_qrcode)
        service_source = inspect.getsource(qrcode_service.get_transparent_qrcode_image_path)

        self.assertIn("get_transparent_qrcode_image_path", route_source)
        self.assertIn("Image.open", service_source)
        self.assertIn("format=\"PNG\"", service_source)
        self.assertIn("TRANSPARENT_QRCODE_IMAGE_DIR", inspect.getsource(qrcode_service))

    def test_high_risk_confirm_routes_reject_placeholder_success(self):
        from routers import admin as admin_router

        source = inspect.getsource(admin_router.verify_confirm_code)
        password_source = inspect.getsource(admin_router.verify_operation_password)
        update_password_source = inspect.getsource(admin_router.update_operation_password)

        self.assertNotIn("code 不为空即通过", source)
        self.assertIn("_ensure_super_admin(admin)", source)
        self.assertIn("操作密码未设置", source)
        self.assertIn("确认码错误", source)
        self.assertIn("operation_password_hash", password_source)
        self.assertIn("操作密码未设置", password_source)
        self.assertIn("_ensure_super_admin(admin)", update_password_source)
        self.assertIn("body.old_password", update_password_source)
        self.assertIn("旧操作密码错误", update_password_source)
        self.assertIn("hash_password(body.password)", update_password_source)


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

    def test_activity_products_require_date_time_slot_and_use_inventory_calendar(self):
        from services import order_service

        create_source = inspect.getsource(order_service.create_order)
        quote_source = inspect.getsource(order_service.quote_order)

        self.assertEqual(order_service.ACTIVITY_PRODUCT_TYPES, {"daily_activity", "special_activity"})
        self.assertIn("DATE_INVENTORY_PRODUCT_TYPES", inspect.getsource(order_service))
        self.assertIn("is_activity_product = product.type in ACTIVITY_PRODUCT_TYPES", create_source)
        self.assertIn("is_activity_product = product.type in ACTIVITY_PRODUCT_TYPES", quote_source)
        self.assertIn("活动商品请选择预约日期", create_source)
        self.assertIn("活动商品请选择预约日期", quote_source)
        self.assertIn("活动商品请选择预约时间", create_source)
        self.assertIn("活动商品请选择预约时间", quote_source)
        self.assertIn("if not is_date_inventory_product:", create_source)
        self.assertIn("if not is_date_inventory_product:", quote_source)
        self.assertIn("if not is_date_inventory_product:", create_source)
        self.assertIn("if not is_date_inventory_product:", quote_source)
        self.assertNotIn("if not is_campsite_product:\n                dates = []", create_source)
        self.assertNotIn("if not is_campsite_product:\n            dates = []", quote_source)

    def test_inventory_calendar_and_order_filters_keep_sku_and_time_slot_dimensions(self):
        from schemas.order import OrderListParams
        from services import inventory_calendar_service, order_service
        from routers import orders

        calendar_source = inspect.getsource(inventory_calendar_service.get_inventory_calendar)
        order_query_source = inspect.getsource(order_service.build_order_list_query)
        list_signature = inspect.signature(order_service.list_orders)
        admin_list_source = inspect.getsource(orders.admin_list_orders)

        self.assertIn("time_slots_by_product", calendar_source)
        self.assertIn("for row_time_slot in target_time_slots", calendar_source)
        self.assertIn("time_slot_filter_provided", calendar_source)
        self.assertNotIn("Inventory.time_slot.is_(None)", calendar_source)
        self.assertIn('"time_slot": target.time_slot', calendar_source)
        self.assertIn("time_slot=target.time_slot", calendar_source)

        fields = OrderListParams.model_fields
        self.assertIn("sku_id", fields)
        self.assertIn("time_slot", fields)
        self.assertIn("sku_id", list_signature.parameters)
        self.assertIn("time_slot", list_signature.parameters)
        self.assertIn("OrderItem.sku_id == sku_id", order_query_source)
        self.assertIn("OrderItem.time_slot == time_slot", order_query_source)
        self.assertIn("sku_id=params.sku_id", admin_list_source)
        self.assertIn("time_slot=params.time_slot", admin_list_source)

    def test_activity_time_slot_contract_covers_quote_seckill_and_migration(self):
        from schemas.order import OrderQuoteItemResponse, SeckillOrderCreateRequest
        from services import product_service
        from services import order_service
        from routers import orders
        from routers import products

        quote_source = inspect.getsource(order_service.quote_order)
        seckill_source = inspect.getsource(order_service.seckill_order)
        seckill_route_source = inspect.getsource(orders.seckill_order)
        service_source = inspect.getsource(order_service)
        price_route_source = inspect.getsource(products.get_price_calendar)
        price_service_source = inspect.getsource(product_service.get_price_calendar)

        self.assertIn("time_slot", OrderQuoteItemResponse.model_fields)
        self.assertIn("time_slot", SeckillOrderCreateRequest.model_fields)
        self.assertIn('"time_slot": time_slot', quote_source)
        self.assertIn('getattr(body, "time_slot", None)', seckill_route_source)
        self.assertIn('time_slot=getattr(body, "time_slot", None)', seckill_route_source)
        self.assertIn("seckill_stock:{product_id}:{booking_date}:{sku_id or 0}:{time_slot or ''}", seckill_source)
        self.assertIn('"time_slot": time_slot', seckill_source)
        self.assertIn("_lock_static_sku_stock", service_source)
        self.assertIn(".with_for_update()", inspect.getsource(order_service._lock_static_sku_stock))
        self.assertIn("_quote_static_sku_stock", service_source)
        self.assertIn("time_slot", inspect.signature(products.get_price_calendar).parameters)
        self.assertIn("time_slot", inspect.signature(product_service.get_price_calendar).parameters)
        self.assertIn("time_slot=time_slot", price_route_source)
        self.assertIn("Inventory.time_slot == time_slot", price_service_source)

        migration_path = Path("alembic/versions/2b3c4d5e6f70_v1_8_add_activity_meeting_point.py")
        migration_source = migration_path.read_text(encoding="utf-8")
        self.assertIn('down_revision: Union[str, None] = "1a2b3c4d5e6f"', migration_source)
        self.assertIn('op.add_column', migration_source)
        self.assertIn('"product_ext_activity"', migration_source)
        self.assertIn('"meeting_point"', migration_source)

    def test_inventory_dimension_queries_handle_null_sku_and_time_slot_explicitly(self):
        from services import inventory_service, order_service

        lock_source = inspect.getsource(inventory_service.lock_inventory)
        release_source = inspect.getsource(inventory_service.release_inventory)
        confirm_source = inspect.getsource(inventory_service.confirm_sell)
        quote_source = inspect.getsource(order_service._quote_inventory_for_order_item)

        for source in [lock_source, release_source, confirm_source, quote_source]:
            self.assertIn("Inventory.sku_id.is_(None)", source)
            self.assertIn("Inventory.time_slot.is_(None)", source)

    def test_refund_inventory_locks_row_and_rejects_partial_stock_recovery(self):
        from services import order_service

        source = inspect.getsource(order_service._refund_inventory)
        self.assertIn(".with_for_update()", source)
        self.assertIn("inv.sold < quantity", source)
        self.assertIn("库存已售数量不足", source)
        self.assertNotIn("refund_qty = min(quantity, inv.sold)", source)

    def test_timeout_release_restores_static_sku_and_new_seckill_dimensions(self):
        from tasks import inventory

        source = inspect.getsource(inventory.task_inventory_auto_release)
        self.assertIn("SKU", inspect.getsource(inventory))
        self.assertIn("item.sku_id", source)
        self.assertIn("sku.stock += item.quantity", source)
        self.assertIn("seckill_stock:{item.product_id}:{item.date}:{item.sku_id or 0}:{item.time_slot or ''}", source)
        self.assertIn("seckill_sold_out:{item.product_id}:{item.sku_id or 0}:{item.time_slot or ''}", source)

    def test_seckill_consistency_check_reads_new_sku_and_time_slot_key_shape(self):
        from tasks import inventory

        source = inspect.getsource(inventory.task_inventory_consistency_check)
        self.assertIn("len(parts) not in {3, 5}", source)
        self.assertIn("sku_id = int(parts[3])", source)
        self.assertIn('time_slot = parts[4] or None', source)
        self.assertIn("Inventory.sku_id.is_(None)", source)
        self.assertIn("Inventory.time_slot == time_slot", source)


if __name__ == "__main__":
    unittest.main()
