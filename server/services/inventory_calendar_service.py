"""
v1.8 完整库存日历与批量库存管理服务。

普通日期库存以 inventory 为事实源；显式绑定共享库存池的商品/SKU
以 inventory_pool 为事实源，日期库存批量调整不得绕过共享池。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.inventory_pool import InventoryPool, InventoryPoolBinding
from models.product import DateTypeConfig, Inventory, InventoryLog, PricingRule, Product, ProductExtActivity, SKU
from services.inventory_pool_service import get_declared_inventory_pool, resolve_declared_inventory_pool


MAX_CALENDAR_DAYS = 93


@dataclass(frozen=True)
class InventoryCalendarTarget:
    """库存日历的一行目标。"""

    product_id: int
    sku_id: Optional[int] = None
    time_slot: Optional[str] = None


def recompute_available(*, total: int, locked: int, sold: int) -> int:
    """按库存不变量重新计算可用库存。"""
    values = {"total": total, "locked": locked, "sold": sold}
    negative_fields = [name for name, value in values.items() if value < 0]
    if negative_fields:
        raise ValueError(f"库存数量不能为负数: {', '.join(negative_fields)}")
    if total < locked + sold:
        raise ValueError("总库存不能小于锁定库存与已售库存之和")
    return total - locked - sold


def _coerce_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def expand_batch_dates(
    *,
    date_start: Optional[date | str],
    date_end: Optional[date | str],
    dates: Optional[Iterable[date | str]],
    weekdays: Optional[Iterable[int]],
) -> list[date]:
    """展开批量操作日期，支持显式日期或范围 + 星期过滤。"""
    weekday_set = {int(day) for day in weekdays or []}
    if any(day < 0 or day > 6 for day in weekday_set):
        raise ValueError("weekdays 必须使用 0-6 表示周一到周日")

    if dates:
        expanded = sorted({_coerce_date(item) for item in dates})
    else:
        if date_start is None or date_end is None:
            raise ValueError("请提供 dates 或 date_start/date_end")
        start = _coerce_date(date_start)
        end = _coerce_date(date_end)
        if start > end:
            raise ValueError("date_start 不能晚于 date_end")
        if (end - start).days + 1 > MAX_CALENDAR_DAYS:
            raise ValueError(f"单次库存日历操作不能超过 {MAX_CALENDAR_DAYS} 天")

        expanded = []
        current = start
        while current <= end:
            if not weekday_set or current.weekday() in weekday_set:
                expanded.append(current)
            current += timedelta(days=1)

    if not expanded:
        raise ValueError("没有可操作的日期")
    return expanded


def ensure_targets_not_pool_bound(
    targets: Iterable[Any],
    *,
    bound_pool_map: dict[tuple[int, Optional[int]], Any],
) -> None:
    """普通日期库存批量写入前，拒绝共享库存池目标。"""
    blocked: list[str] = []
    for target in targets:
        product_id = int(getattr(target, "product_id"))
        sku_id = getattr(target, "sku_id", None)
        pool = bound_pool_map.get((product_id, sku_id))
        if pool:
            label = f"product_id={product_id}"
            if sku_id is not None:
                label += f", sku_id={sku_id}"
            blocked.append(f"{label} 已绑定共享库存池 {getattr(pool, 'pool_code', pool.id)}")
    if blocked:
        raise ValueError("共享库存池目标不能通过普通日期库存批量调整：" + "；".join(blocked))


def _date_type_for(current_date: date, date_type_map: dict[date, str]) -> str:
    if current_date in date_type_map:
        return date_type_map[current_date]
    return "weekend" if current_date.weekday() >= 5 else "weekday"


def _price_for(
    *,
    product: Product,
    sku: Optional[SKU],
    current_date: date,
    date_type: str,
    custom_date_prices: dict[tuple[int, date], Decimal],
    date_type_prices: dict[tuple[int, str], Decimal],
) -> Decimal:
    if sku is not None:
        return sku.price
    custom_price = custom_date_prices.get((product.id, current_date))
    if custom_price is not None:
        return custom_price
    typed_price = date_type_prices.get((product.id, date_type))
    if typed_price is not None:
        return typed_price
    return product.base_price


def _sku_label(sku: Optional[SKU]) -> Optional[str]:
    if sku is None:
        return None
    spec_values = sku.spec_values or {}
    spec_label = " / ".join(str(value) for value in spec_values.values())
    return spec_label or sku.sku_code


def build_inventory_calendar_cell(
    *,
    product: Any,
    sku: Optional[Any],
    current_date: date,
    date_type: str,
    price: Decimal | int | float,
    inventory: Optional[Any],
    inventory_pool: Optional[Any],
    time_slot: Optional[str] = None,
) -> dict[str, Any]:
    """构建单个库存日历格子。"""
    cell_time_slot = getattr(inventory, "time_slot", None) if inventory is not None else time_slot
    if inventory_pool is not None:
        pool_status = getattr(inventory_pool, "status", "inactive")
        return {
            "date": current_date,
            "date_type": date_type,
            "product_id": product.id,
            "product_name": product.name,
            "sku_id": getattr(sku, "id", None),
            "sku_code": getattr(sku, "sku_code", None),
            "sku_name": _sku_label(sku),
            "time_slot": cell_time_slot,
            "price": price,
            "inventory_source": "inventory_pool",
            "inventory_id": None,
            "inventory_pool_id": inventory_pool.id,
            "inventory_pool_code": getattr(inventory_pool, "pool_code", None),
            "inventory_pool_name": getattr(inventory_pool, "name", None),
            "total": int(getattr(inventory_pool, "total", 0) or 0),
            "available": int(getattr(inventory_pool, "available", 0) or 0),
            "locked": int(getattr(inventory_pool, "locked", 0) or 0),
            "sold": int(getattr(inventory_pool, "sold", 0) or 0),
            "status": "open" if pool_status == "active" else "closed",
            "editable": False,
            "edit_reason": "共享库存池是交易事实源，请在共享库存池中调整",
        }

    if inventory is None:
        total = available = locked = sold = 0
        inv_status = "closed"
        inventory_id = None
    else:
        total = int(getattr(inventory, "total", 0) or 0)
        locked = int(getattr(inventory, "locked", 0) or 0)
        sold = int(getattr(inventory, "sold", 0) or 0)
        available = recompute_available(total=total, locked=locked, sold=sold)
        inv_status = getattr(inventory, "status", "closed")
        inventory_id = getattr(inventory, "id", None)

    return {
        "date": current_date,
        "date_type": date_type,
        "product_id": product.id,
        "product_name": product.name,
        "sku_id": getattr(sku, "id", None),
        "sku_code": getattr(sku, "sku_code", None),
        "sku_name": _sku_label(sku),
        "time_slot": cell_time_slot,
        "price": price,
        "inventory_source": "inventory",
        "inventory_id": inventory_id,
        "inventory_pool_id": None,
        "inventory_pool_code": None,
        "inventory_pool_name": None,
        "total": total,
        "available": available,
        "locked": locked,
        "sold": sold,
        "status": inv_status,
        "editable": True,
        "edit_reason": None,
    }


async def _load_products(
    db: AsyncSession,
    *,
    site_id: int,
    product_ids: Optional[list[int]],
    product_type: Optional[str] = None,
) -> list[Product]:
    conditions = [
        Product.site_id == site_id,
        Product.is_deleted.is_(False),
    ]
    if product_ids:
        conditions.append(Product.id.in_(product_ids))
    if product_type:
        conditions.append(Product.type == product_type)

    result = await db.execute(
        select(Product)
        .where(*conditions)
        .order_by(Product.sort_order.desc(), Product.id.desc())
    )
    products = list(result.scalars().all())
    if product_ids and len({product.id for product in products}) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="存在不属于当前营地的商品")
    return products


async def _load_skus(
    db: AsyncSession,
    *,
    site_id: int,
    product_ids: list[int],
    sku_ids: Optional[list[int]],
) -> list[SKU]:
    if not product_ids and not sku_ids:
        return []
    conditions = [
        SKU.is_deleted.is_(False),
        Product.site_id == site_id,
        Product.is_deleted.is_(False),
    ]
    if product_ids:
        conditions.append(SKU.product_id.in_(product_ids))
    if sku_ids:
        conditions.append(SKU.id.in_(sku_ids))

    result = await db.execute(
        select(SKU)
        .join(Product, Product.id == SKU.product_id)
        .where(*conditions)
        .order_by(SKU.id.asc())
    )
    skus = list(result.scalars().all())
    if sku_ids and len({sku.id for sku in skus}) != len(set(sku_ids)):
        raise HTTPException(status_code=400, detail="存在不属于当前营地的 SKU")
    return skus


def _format_activity_time_slot(slot: Any) -> Optional[str]:
    """将活动扩展里的场次对象规整成订单库存使用的 time_slot 字符串。"""
    if not isinstance(slot, dict):
        value = str(slot or "").strip()
        return value or None
    start = str(slot.get("start") or "").strip()
    end = str(slot.get("end") or "").strip()
    if start and end:
        return f"{start}-{end}"
    value = str(slot.get("time_slot") or slot.get("label") or "").strip()
    return value or None


async def _load_activity_time_slots(
    db: AsyncSession,
    *,
    product_ids: list[int],
) -> dict[int, list[str]]:
    """读取活动商品配置的场次，用于库存日历按场次展开行。"""
    if not product_ids:
        return {}
    result = await db.execute(
        select(ProductExtActivity).where(ProductExtActivity.product_id.in_(product_ids))
    )
    time_slots_by_product: dict[int, list[str]] = {}
    for ext in result.scalars().all():
        seen: set[str] = set()
        slots: list[str] = []
        for raw_slot in ext.time_slots or []:
            slot = _format_activity_time_slot(raw_slot)
            if slot and slot not in seen:
                seen.add(slot)
                slots.append(slot)
        if slots:
            time_slots_by_product[ext.product_id] = slots
    return time_slots_by_product


async def _load_declared_pool_map(
    db: AsyncSession,
    *,
    site_id: int,
    targets: list[InventoryCalendarTarget],
) -> dict[tuple[int, Optional[int]], InventoryPool]:
    product_ids = {target.product_id for target in targets}
    sku_ids = {target.sku_id for target in targets if target.sku_id is not None}
    if not product_ids and not sku_ids:
        return {}

    conditions = []
    if product_ids:
        conditions.append(InventoryPoolBinding.product_id.in_(product_ids))
    if sku_ids:
        conditions.append(InventoryPoolBinding.sku_id.in_(sku_ids))
    result = await db.execute(
        select(InventoryPoolBinding, InventoryPool)
        .join(InventoryPool, InventoryPool.id == InventoryPoolBinding.inventory_pool_id)
        .where(
            InventoryPool.site_id == site_id,
            InventoryPool.is_deleted.is_(False),
            InventoryPoolBinding.site_id == site_id,
            InventoryPoolBinding.is_deleted.is_(False),
            or_(*conditions),
        )
        .order_by(InventoryPoolBinding.priority.asc(), InventoryPoolBinding.id.asc())
    )
    rows = result.all()
    bindings = [row[0] for row in rows]
    pools = {row[1].id: row[1] for row in rows}
    bound_map: dict[tuple[int, Optional[int]], InventoryPool] = {}
    for target in targets:
        pool = resolve_declared_inventory_pool(
            bindings,
            pools=pools,
            product_id=target.product_id,
            sku_id=target.sku_id,
        )
        if pool is not None:
            bound_map[(target.product_id, target.sku_id)] = pool
    return bound_map


async def get_inventory_calendar(
    db: AsyncSession,
    *,
    site_id: int,
    date_start: date,
    date_end: date,
    product_ids: Optional[list[int]] = None,
    product_type: Optional[str] = None,
    sku_ids: Optional[list[int]] = None,
    time_slot: Optional[str] = None,
    inventory_source: str = "all",
    include_missing: bool = True,
) -> dict[str, Any]:
    """查询完整库存日历，缺失日期也返回 closed/0 格子。"""
    dates = expand_batch_dates(date_start=date_start, date_end=date_end, dates=None, weekdays=None)
    if inventory_source not in {"all", "inventory", "inventory_pool"}:
        raise HTTPException(status_code=400, detail="inventory_source 只能为 all/inventory/inventory_pool")

    products = await _load_products(
        db,
        site_id=site_id,
        product_ids=product_ids,
        product_type=product_type,
    )
    product_map = {product.id: product for product in products}
    time_slot_filter_provided = time_slot is not None
    activity_product_ids = [
        product.id for product in products
        if product.type in {"daily_activity", "special_activity"}
    ]
    time_slots_by_product = await _load_activity_time_slots(db, product_ids=activity_product_ids)
    skus = await _load_skus(
        db,
        site_id=site_id,
        product_ids=list(product_map),
        sku_ids=sku_ids,
    )
    sku_map = {sku.id: sku for sku in skus}
    skus_by_product: dict[int, list[SKU]] = {}
    for sku in skus:
        skus_by_product.setdefault(sku.product_id, []).append(sku)

    base_targets: list[InventoryCalendarTarget] = [InventoryCalendarTarget(product_id=product.id) for product in products]
    if sku_ids:
        base_targets = [InventoryCalendarTarget(product_id=sku.product_id, sku_id=sku.id) for sku in skus]
    else:
        for sku in skus:
            base_targets.append(InventoryCalendarTarget(product_id=sku.product_id, sku_id=sku.id))

    targets: list[InventoryCalendarTarget] = []
    for base_target in base_targets:
        product = product_map[base_target.product_id]
        configured_slots = time_slots_by_product.get(product.id, [])
        if time_slot_filter_provided:
            target_time_slots = [time_slot]
        elif product.type in {"daily_activity", "special_activity"} and configured_slots:
            target_time_slots = configured_slots
        else:
            target_time_slots = [None]
        for row_time_slot in target_time_slots:
            targets.append(
                InventoryCalendarTarget(
                    product_id=base_target.product_id,
                    sku_id=base_target.sku_id,
                    time_slot=row_time_slot,
                )
            )

    bound_pool_map = await _load_declared_pool_map(db, site_id=site_id, targets=targets)

    inv_conditions = [
        Inventory.site_id == site_id,
        Inventory.product_id.in_([target.product_id for target in targets] or [-1]),
        Inventory.date >= date_start,
        Inventory.date <= date_end,
        Inventory.is_deleted.is_(False),
    ]
    if sku_ids:
        inv_conditions.append(Inventory.sku_id.in_(sku_ids))
    if time_slot_filter_provided:
        inv_conditions.append(Inventory.time_slot == time_slot)
    inv_result = await db.execute(select(Inventory).where(*inv_conditions))
    inventory_map = {
        (inv.product_id, inv.sku_id, inv.date, inv.time_slot): inv
        for inv in inv_result.scalars().all()
    }

    dt_result = await db.execute(
        select(DateTypeConfig).where(
            DateTypeConfig.site_id == site_id,
            DateTypeConfig.date >= date_start,
            DateTypeConfig.date <= date_end,
            DateTypeConfig.is_deleted.is_(False),
        )
    )
    date_type_map = {item.date: item.date_type for item in dt_result.scalars().all()}

    pricing_result = await db.execute(
        select(PricingRule).where(
            PricingRule.product_id.in_(list(product_map) or [-1]),
            PricingRule.is_deleted.is_(False),
        )
    )
    custom_date_prices: dict[tuple[int, date], Decimal] = {}
    date_type_prices: dict[tuple[int, str], Decimal] = {}
    for rule in pricing_result.scalars().all():
        if rule.rule_type == "custom_date" and rule.custom_date:
            custom_date_prices[(rule.product_id, rule.custom_date)] = rule.price
        elif rule.rule_type == "date_type" and rule.date_type:
            date_type_prices[(rule.product_id, rule.date_type)] = rule.price

    rows = []
    cells = []
    for target in targets:
        product = product_map[target.product_id]
        sku = sku_map.get(target.sku_id) if target.sku_id is not None else None
        pool = bound_pool_map.get((target.product_id, target.sku_id))
        target_source = "inventory_pool" if pool else "inventory"
        if inventory_source != "all" and target_source != inventory_source:
            continue
        rows.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "sku_id": target.sku_id,
                "sku_code": getattr(sku, "sku_code", None),
                "sku_name": _sku_label(sku),
                "time_slot": target.time_slot,
                "inventory_source": target_source,
                "inventory_pool_id": getattr(pool, "id", None),
                "inventory_pool_code": getattr(pool, "pool_code", None),
                "inventory_pool_name": getattr(pool, "name", None),
            }
        )
        for current_date in dates:
            inv = inventory_map.get((target.product_id, target.sku_id, current_date, target.time_slot))
            if inv is None and not include_missing and pool is None:
                continue
            date_type = _date_type_for(current_date, date_type_map)
            price = _price_for(
                product=product,
                sku=sku,
                current_date=current_date,
                date_type=date_type,
                custom_date_prices=custom_date_prices,
                date_type_prices=date_type_prices,
            )
            cells.append(
                build_inventory_calendar_cell(
                    product=product,
                    sku=sku,
                    current_date=current_date,
                    date_type=date_type,
                    price=price,
                    inventory=inv,
                    inventory_pool=pool,
                    time_slot=target.time_slot,
                )
            )

    return {
        "date_start": date_start,
        "date_end": date_end,
        "rows": rows,
        "cells": cells,
    }


def _normalize_int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(item) for item in value if item is not None]
    return [int(value)]


async def _load_batch_targets(
    db: AsyncSession,
    *,
    site_id: int,
    product_ids: list[int],
    sku_ids: list[int],
) -> list[InventoryCalendarTarget]:
    if not product_ids and not sku_ids:
        raise HTTPException(status_code=400, detail="请提供 product_ids 或 sku_ids")

    if sku_ids and not product_ids:
        skus = await _load_skus(
            db,
            site_id=site_id,
            product_ids=[],
            sku_ids=sku_ids,
        )
        return [InventoryCalendarTarget(product_id=sku.product_id, sku_id=sku.id) for sku in skus]

    products = await _load_products(db, site_id=site_id, product_ids=product_ids or None)
    product_map = {product.id: product for product in products}
    skus = await _load_skus(
        db,
        site_id=site_id,
        product_ids=list(product_map) or product_ids,
        sku_ids=sku_ids or None,
    )
    if sku_ids:
        return [InventoryCalendarTarget(product_id=sku.product_id, sku_id=sku.id) for sku in skus]
    return [InventoryCalendarTarget(product_id=product.id) for product in products]


def _next_total_for_mode(
    *,
    mode: str,
    existing_total: int,
    requested_total: Optional[int],
    delta: Optional[int],
) -> Optional[int]:
    if mode in {"set_total", "open"}:
        if requested_total is None:
            return existing_total if mode == "open" else None
        return int(requested_total)
    if mode == "adjust_total":
        if delta is None:
            return None
        return existing_total + int(delta)
    if mode == "close":
        return requested_total if requested_total is not None else existing_total
    raise HTTPException(status_code=400, detail="mode 只能为 set_total/adjust_total/open/close")


async def batch_upsert_inventory(
    db: AsyncSession,
    *,
    site_id: int,
    body: dict[str, Any],
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """批量创建或调整普通日期库存。"""
    product_ids = _normalize_int_list(body.get("product_ids") or body.get("product_id"))
    sku_ids = _normalize_int_list(body.get("sku_ids") or body.get("sku_id"))
    dates = expand_batch_dates(
        date_start=body.get("date_start") or body.get("start_date"),
        date_end=body.get("date_end") or body.get("end_date"),
        dates=body.get("dates"),
        weekdays=body.get("weekdays"),
    )
    mode = body.get("mode") or "set_total"
    requested_total = body.get("total")
    if requested_total is None and body.get("total_per_day") is not None:
        requested_total = body.get("total_per_day")
    requested_total = int(requested_total) if requested_total is not None else None
    delta = int(body["delta"]) if body.get("delta") is not None else None
    inv_status = body.get("status")
    create_missing = bool(body.get("create_missing", True))
    time_slot = body.get("time_slot")
    remark = body.get("remark")

    targets = await _load_batch_targets(
        db,
        site_id=site_id,
        product_ids=product_ids,
        sku_ids=sku_ids,
    )
    bound_pool_map = await _load_declared_pool_map(db, site_id=site_id, targets=targets)
    try:
        ensure_targets_not_pool_bound(targets, bound_pool_map=bound_pool_map)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    inv_conditions = [
        Inventory.site_id == site_id,
        Inventory.date.in_(dates),
        Inventory.product_id.in_([target.product_id for target in targets]),
        Inventory.is_deleted.is_(False),
    ]
    target_sku_ids = [target.sku_id for target in targets if target.sku_id is not None]
    if target_sku_ids:
        inv_conditions.append(Inventory.sku_id.in_(target_sku_ids))
    else:
        inv_conditions.append(Inventory.sku_id.is_(None))
    if time_slot is None:
        inv_conditions.append(Inventory.time_slot.is_(None))
    else:
        inv_conditions.append(Inventory.time_slot == time_slot)

    inv_result = await db.execute(select(Inventory).where(*inv_conditions))
    existing_map = {
        (inv.product_id, inv.sku_id, inv.date, inv.time_slot): inv
        for inv in inv_result.scalars().all()
    }

    created_count = updated_count = skipped_count = matched_count = 0
    errors: list[dict[str, Any]] = []
    for target in targets:
        for current_date in dates:
            key = (target.product_id, target.sku_id, current_date, time_slot)
            inv = existing_map.get(key)
            if inv is None and not create_missing:
                skipped_count += 1
                continue

            if inv is None:
                base_total = 0
                locked = sold = 0
            else:
                base_total = int(inv.total or 0)
                locked = int(inv.locked or 0)
                sold = int(inv.sold or 0)
                matched_count += 1

            next_total = _next_total_for_mode(
                mode=mode,
                existing_total=base_total,
                requested_total=requested_total,
                delta=delta,
            )
            if next_total is None:
                raise HTTPException(status_code=400, detail="当前 mode 需要提供 total 或 delta")
            try:
                available = recompute_available(total=next_total, locked=locked, sold=sold)
            except ValueError as exc:
                errors.append(
                    {
                        "product_id": target.product_id,
                        "sku_id": target.sku_id,
                        "date": current_date.isoformat(),
                        "message": str(exc),
                    }
                )
                continue

            if inv is None:
                inv = Inventory(
                    site_id=site_id,
                    product_id=target.product_id,
                    sku_id=target.sku_id,
                    date=current_date,
                    time_slot=time_slot,
                    total=next_total,
                    available=available,
                    locked=0,
                    sold=0,
                    status=inv_status or ("closed" if mode == "close" else "open"),
                )
                db.add(inv)
                existing_map[key] = inv
                created_count += 1
                continue

            old_total = inv.total
            inv.total = next_total
            inv.available = available
            if inv_status is not None:
                inv.status = inv_status
            elif mode == "open":
                inv.status = "open"
            elif mode == "close":
                inv.status = "closed"
            if old_total != inv.total or inv_status is not None or mode in {"open", "close"}:
                db.add(
                    InventoryLog(
                        inventory_id=inv.id,
                        change_type="manual_adjust",
                        quantity=int(inv.total or 0) - int(old_total or 0),
                        operator_id=operator_id,
                        remark=remark or "批量库存调整",
                    )
                )
            updated_count += 1

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40904, "message": "部分库存调整会破坏库存不变量", "errors": errors},
        )

    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40905, "message": "库存日历已被并发请求更新，请刷新后重试"},
        ) from exc
    return {
        "matched_count": matched_count,
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


async def update_inventory_cell(
    db: AsyncSession,
    *,
    site_id: int,
    inventory_id: int,
    body: dict[str, Any],
    operator_id: Optional[int] = None,
) -> Inventory:
    """安全更新单个普通库存格。"""
    result = await db.execute(
        select(Inventory)
        .where(
            Inventory.id == inventory_id,
            Inventory.site_id == site_id,
            Inventory.is_deleted.is_(False),
        )
        .with_for_update()
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="库存记录不存在")

    pool = await get_declared_inventory_pool(
        db,
        site_id=site_id,
        product_id=inv.product_id,
        sku_id=inv.sku_id,
    )
    if pool is not None:
        raise HTTPException(status_code=409, detail="该商品/SKU 已绑定共享库存池，请调整共享库存池")

    old_total = inv.total
    if body.get("total") is not None:
        total = int(body["total"])
        inv.available = recompute_available(total=total, locked=inv.locked, sold=inv.sold)
        inv.total = total
    if body.get("status") is not None:
        inv.status = body["status"]
    if body.get("total") is not None:
        db.add(
            InventoryLog(
                inventory_id=inv.id,
                change_type="manual_adjust",
                quantity=int(inv.total or 0) - int(old_total or 0),
                operator_id=operator_id,
                remark=body.get("remark") or "单日库存调整",
            )
        )
    await db.flush()
    return inv
