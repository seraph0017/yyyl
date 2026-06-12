"""
西郊林场演示数据脚本。

用于线上或本地补齐 C 端小程序审核展示数据。脚本按 site_id=1 和商品名称做
upsert，可重复执行，不清空任何表，不创建订单、票券或支付流水。

用法:
    cd server
    python seed_xijiao_demo_data.py

建议同时执行:
    python seed_admin.py
"""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select

import models  # noqa: F401  # 确保 SQLAlchemy 注册全部模型
from database import async_session_factory, engine
from models.content import PageConfig
from models.product import (
    DiscountRule,
    Inventory,
    PricingRule,
    Product,
    ProductExtActivity,
    ProductExtCamping,
    ProductExtRental,
    ProductExtShop,
    SKU,
)
from seed_products import HOME_BANNERS, HOME_NOTICE, PRICING_RULES, PRODUCTS, SKUS

SITE_ID = 1
INVENTORY_DAYS = 45
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "admin123456"


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _calculate_available(total: int, sold: int, locked: int) -> int:
    return max(total - sold - locked, 0)


def _normal_product_data(data: dict[str, Any]) -> dict[str, Any]:
    item = data.copy()
    item["images"] = _json_value(item.get("images", []))
    item["site_id"] = SITE_ID
    return item


async def upsert_product(session, source: dict[str, Any]) -> Product:
    data = _normal_product_data(source)
    result = await session.execute(
        select(Product).where(
            Product.site_id == SITE_ID,
            Product.name == data["name"],
            Product.is_deleted.is_(False),
        )
    )
    product = result.scalar_one_or_none()

    if product is None:
        product = Product(**data)
        session.add(product)
        await session.flush()
        return product

    for key, value in data.items():
        if hasattr(product, key):
            setattr(product, key, value)
    await session.flush()
    return product


async def upsert_one_to_one_ext(session, model, product_id: int, data: dict[str, Any]) -> None:
    normalized = {key: _json_value(value) for key, value in data.items()}
    result = await session.execute(select(model).where(model.product_id == product_id))
    ext = result.scalar_one_or_none()

    if ext is None:
        session.add(model(product_id=product_id, **normalized))
        return

    for key, value in normalized.items():
        setattr(ext, key, value)


async def upsert_skus(session, product_id: int, product_name: str) -> int:
    count = 0
    for source in SKUS.get(product_name, []):
        data = source.copy()
        data["spec_values"] = _json_value(data["spec_values"])
        result = await session.execute(select(SKU).where(SKU.sku_code == data["sku_code"]))
        sku = result.scalar_one_or_none()

        if sku is None:
            session.add(SKU(product_id=product_id, **data))
        else:
            sku.product_id = product_id
            for key, value in data.items():
                setattr(sku, key, value)
        count += 1
    return count


async def upsert_pricing_rules(session, product_id: int, product_name: str) -> int:
    count = 0
    for source in PRICING_RULES.get(product_name, []):
        data = source.copy()
        result = await session.execute(
            select(PricingRule).where(
                PricingRule.product_id == product_id,
                PricingRule.rule_type == data["rule_type"],
                PricingRule.date_type == data.get("date_type"),
                PricingRule.custom_date.is_(None),
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            session.add(PricingRule(product_id=product_id, **data))
        else:
            rule.price = Decimal(str(data["price"]))
        count += 1
    return count


async def upsert_inventory(session, product_id: int, product_name: str) -> int:
    if "营位" not in product_name:
        return 0

    total = 1 if any(code in product_name for code in ("A0", "B0", "C0", "D0", "E0")) else 20
    count = 0
    today = date.today()

    for day_offset in range(INVENTORY_DAYS):
        inventory_date = today + timedelta(days=day_offset)
        result = await session.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.site_id == SITE_ID,
                Inventory.date == inventory_date,
                Inventory.sku_id.is_(None),
            )
        )
        inventory = result.scalar_one_or_none()
        if inventory is None:
            session.add(
                Inventory(
                    product_id=product_id,
                    date=inventory_date,
                    total=total,
                    available=total,
                    locked=0,
                    sold=0,
                    status="open",
                    site_id=SITE_ID,
                )
            )
        else:
            inventory.total = max(inventory.total, total)
            inventory.available = _calculate_available(
                inventory.total,
                inventory.sold,
                inventory.locked,
            )
            inventory.status = "open"
        count += 1
    return count


async def upsert_page_config(session, page_key: str, config_data: dict[str, Any]) -> None:
    result = await session.execute(
        select(PageConfig).where(PageConfig.page_key == page_key, PageConfig.site_id == SITE_ID)
    )
    page_config = result.scalar_one_or_none()
    if page_config is None:
        session.add(PageConfig(page_key=page_key, config_data=config_data, status="active", site_id=SITE_ID))
    else:
        page_config.config_data = config_data
        page_config.status = "active"


async def upsert_discount_rules(session) -> int:
    rules = [
        {"rule_type": "consecutive_days", "threshold": 3, "discount_rate": Decimal("0.90")},
        {"rule_type": "consecutive_days", "threshold": 5, "discount_rate": Decimal("0.85")},
        {"rule_type": "multi_person", "threshold": 3, "discount_rate": Decimal("0.95")},
    ]
    count = 0
    for data in rules:
        result = await session.execute(
            select(DiscountRule).where(
                DiscountRule.site_id == SITE_ID,
                DiscountRule.product_id.is_(None),
                DiscountRule.rule_type == data["rule_type"],
                DiscountRule.threshold == data["threshold"],
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            session.add(DiscountRule(**data, status="active", site_id=SITE_ID))
        else:
            rule.discount_rate = data["discount_rate"]
            rule.status = "active"
        count += 1
    return count


async def seed() -> None:
    products_created_or_updated = 0
    sku_count = 0
    pricing_count = 0
    inventory_count = 0

    async with async_session_factory() as session:
        try:
            for raw_item in copy.deepcopy(PRODUCTS):
                ext_camping = raw_item.pop("ext_camping", None)
                ext_rental = raw_item.pop("ext_rental", None)
                ext_activity = raw_item.pop("ext_activity", None)
                ext_shop = raw_item.pop("ext_shop", None)

                product = await upsert_product(session, raw_item)
                products_created_or_updated += 1

                if ext_camping:
                    await upsert_one_to_one_ext(session, ProductExtCamping, product.id, ext_camping)
                if ext_rental:
                    await upsert_one_to_one_ext(session, ProductExtRental, product.id, ext_rental)
                if ext_activity:
                    await upsert_one_to_one_ext(session, ProductExtActivity, product.id, ext_activity)
                if ext_shop:
                    await upsert_one_to_one_ext(session, ProductExtShop, product.id, ext_shop)

                sku_count += await upsert_skus(session, product.id, product.name)
                pricing_count += await upsert_pricing_rules(session, product.id, product.name)
                inventory_count += await upsert_inventory(session, product.id, product.name)

            await upsert_page_config(session, "home_banner", {"banners": HOME_BANNERS})
            await upsert_page_config(session, "home_notice", {"text": HOME_NOTICE})
            discount_count = await upsert_discount_rules(session)

            await session.commit()

            print("西郊林场演示数据已补齐")
            print(f"商品: {products_created_or_updated} 件")
            print(f"SKU: {sku_count} 个")
            print(f"定价规则: {pricing_count} 条")
            print(f"库存: {inventory_count} 条")
            print("页面配置: home_banner, home_notice")
            print(f"优惠规则: {discount_count} 条")
            print("\n审核使用说明:")
            print("- 小程序可浏览首页、商品列表、商品详情并创建待支付订单")
            print("- 本脚本不会生成订单/票券/支付流水，避免污染线上经营数据")
            print("- 如需后台审核账号，请执行: python seed_admin.py")
            print(f"- 默认后台账号: {TEST_ADMIN_USERNAME} / {TEST_ADMIN_PASSWORD}")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
