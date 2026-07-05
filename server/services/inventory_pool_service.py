"""
v1.8 跨商品共享库存池服务
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.inventory_pool import InventoryPool, InventoryPoolBinding
from models.product import Product, SKU


TARGET_FIELDS = ("product_id", "sku_id", "activity_session_id", "rental_asset_id")


def get_product_sku_shared_pool_code(site_id: int, product_id: int) -> str:
    """商品编辑器生成的“本商品 SKU 共享库存池”编码。"""
    return f"site{site_id}-product{product_id}-sku-shared"


def validate_pool_numbers(*, total: int, available: int, locked: int, sold: int) -> None:
    """校验库存池数量不变量。

    库存池作为跨商品共享库存事实源，必须始终满足：
    available + locked + sold = total，且各数量不能为负数。
    """
    values = {
        "total": total,
        "available": available,
        "locked": locked,
        "sold": sold,
    }
    negatives = [name for name, value in values.items() if value < 0]
    if negatives:
        raise ValueError(f"库存池数量不能为负数: {', '.join(negatives)}")

    if available + locked + sold != total:
        raise ValueError("库存池数量必须满足 available + locked + sold = total")


def normalize_initial_pool_numbers(data: dict[str, Any]) -> dict[str, int]:
    """归一化新建库存池的初始数量。

    新建库存池不能伪造历史锁定/已售状态；locked/sold 只能由订单状态机维护，
    available 初始值必须等于 total。
    """
    total = int(data.get("total") or 0)
    declared_available = data.get("available")
    declared_locked = data.get("locked")
    declared_sold = data.get("sold")
    available = int(declared_available) if declared_available is not None else total
    locked = int(declared_locked) if declared_locked is not None else 0
    sold = int(declared_sold) if declared_sold is not None else 0

    if available != total or locked != 0 or sold != 0:
        raise ValueError("新建库存池只允许干净初始态：available 必须等于 total，locked/sold 必须为 0")
    validate_pool_numbers(total=total, available=available, locked=locked, sold=sold)
    return {"total": total, "available": available, "locked": locked, "sold": sold}


def get_binding_target_count(data: dict[str, Any]) -> int:
    """统计绑定请求里实际声明了几个目标。"""
    return sum(1 for field in TARGET_FIELDS if data.get(field) is not None)


def validate_exactly_one_binding_target(data: dict[str, Any]) -> None:
    """库存池绑定必须恰好指定一个售卖单元。"""
    if get_binding_target_count(data) != 1:
        raise ValueError("库存池绑定必须且只能指定一个目标")


def resolve_bound_inventory_pool(
    bindings: list[Any],
    *,
    pools: dict[int, Any],
    product_id: Optional[int],
    sku_id: Optional[int] = None,
    activity_session_id: Optional[int] = None,
    rental_asset_id: Optional[int] = None,
) -> Optional[Any]:
    """按显式 active 绑定解析库存池，优先级越小越靠前。"""
    sorted_bindings = sorted(
        bindings,
        key=lambda item: (
            _binding_specificity_rank(
                item,
                product_id=product_id,
                sku_id=sku_id,
                activity_session_id=activity_session_id,
                rental_asset_id=rental_asset_id,
            ),
            getattr(item, "priority", 100),
            getattr(item, "id", 0),
        ),
    )
    for binding in sorted_bindings:
        if getattr(binding, "status", None) != "active":
            continue
        pool = pools.get(getattr(binding, "inventory_pool_id"))
        if not pool or getattr(pool, "status", None) != "active":
            continue
        if sku_id and getattr(binding, "sku_id", None) == sku_id:
            return pool
        if product_id and getattr(binding, "product_id", None) == product_id:
            return pool
        if activity_session_id and getattr(binding, "activity_session_id", None) == activity_session_id:
            return pool
        if rental_asset_id and getattr(binding, "rental_asset_id", None) == rental_asset_id:
            return pool
    return None


def resolve_declared_inventory_pool(
    bindings: list[Any],
    *,
    pools: dict[int, Any],
    product_id: Optional[int],
    sku_id: Optional[int] = None,
    activity_session_id: Optional[int] = None,
    rental_asset_id: Optional[int] = None,
) -> Optional[Any]:
    """按未删除显式绑定解析库存池，不按启停状态回退到普通库存。"""
    sorted_bindings = sorted(
        bindings,
        key=lambda item: (
            _binding_specificity_rank(
                item,
                product_id=product_id,
                sku_id=sku_id,
                activity_session_id=activity_session_id,
                rental_asset_id=rental_asset_id,
            ),
            getattr(item, "priority", 100),
            getattr(item, "id", 0),
        ),
    )
    for binding in sorted_bindings:
        if getattr(binding, "is_deleted", False):
            continue
        pool = pools.get(getattr(binding, "inventory_pool_id"))
        if not pool or getattr(pool, "is_deleted", False):
            continue
        if sku_id and getattr(binding, "sku_id", None) == sku_id:
            return pool
        if product_id and getattr(binding, "product_id", None) == product_id:
            return pool
        if activity_session_id and getattr(binding, "activity_session_id", None) == activity_session_id:
            return pool
        if rental_asset_id and getattr(binding, "rental_asset_id", None) == rental_asset_id:
            return pool
    return None


def _binding_specificity_rank(
    binding: Any,
    *,
    product_id: Optional[int],
    sku_id: Optional[int] = None,
    activity_session_id: Optional[int] = None,
    rental_asset_id: Optional[int] = None,
) -> int:
    """绑定命中优先级：SKU/场次/租赁等具体售卖单元优先于商品级绑定。"""
    if sku_id and getattr(binding, "sku_id", None) == sku_id:
        return 0
    if activity_session_id and getattr(binding, "activity_session_id", None) == activity_session_id:
        return 0
    if rental_asset_id and getattr(binding, "rental_asset_id", None) == rental_asset_id:
        return 0
    if product_id and getattr(binding, "product_id", None) == product_id:
        return 10
    return 100


def _binding_specificity_case(
    *,
    product_id: Optional[int],
    sku_id: Optional[int] = None,
    activity_session_id: Optional[int] = None,
    rental_asset_id: Optional[int] = None,
):
    """SQL 排序表达式：具体售卖单元绑定优先，最后再按 priority/id 排序。"""
    whens = []
    if sku_id:
        whens.append((InventoryPoolBinding.sku_id == sku_id, 0))
    if activity_session_id:
        whens.append((InventoryPoolBinding.activity_session_id == activity_session_id, 0))
    if rental_asset_id:
        whens.append((InventoryPoolBinding.rental_asset_id == rental_asset_id, 0))
    if product_id:
        whens.append((InventoryPoolBinding.product_id == product_id, 10))
    return case(*whens, else_=100)


def validate_pool_availability(pool: Any, *, required_quantity: int) -> None:
    """校验库存池可用量。"""
    if getattr(pool, "status", None) != "active":
        raise ValueError("库存池未启用")
    available = int(getattr(pool, "available", 0) or 0)
    if available < required_quantity:
        raise ValueError(f"库存池库存不足，可用: {available}, 需要: {required_quantity}")


def validate_pool_locked(pool: Any, *, required_quantity: int) -> None:
    """校验库存池锁定量。"""
    locked = int(getattr(pool, "locked", 0) or 0)
    if locked < required_quantity:
        raise ValueError(f"共享库存锁定不足，锁定: {locked}, 需要: {required_quantity}")


async def validate_binding_target_site(
    db: AsyncSession,
    *,
    site_id: int,
    data: dict[str, Any],
) -> None:
    """校验绑定目标归属当前营地。"""
    validate_exactly_one_binding_target(data)

    product_id = data.get("product_id")
    sku_id = data.get("sku_id")
    if data.get("activity_session_id") is not None:
        raise HTTPException(status_code=400, detail="活动场次绑定需等待实体模型接入后启用")
    if data.get("rental_asset_id") is not None:
        raise HTTPException(status_code=400, detail="租赁资产绑定需等待实体模型接入后启用")

    if product_id is not None:
        result = await db.execute(
            select(Product.id).where(
                Product.id == product_id,
                Product.site_id == site_id,
                Product.is_deleted.is_(False),
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="绑定商品不属于当前营地")
    if sku_id is not None:
        result = await db.execute(
            select(SKU.id)
            .join(Product, Product.id == SKU.product_id)
            .where(
                SKU.id == sku_id,
                Product.site_id == site_id,
                SKU.is_deleted.is_(False),
                Product.is_deleted.is_(False),
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="绑定 SKU 不属于当前营地")


async def get_bound_inventory_pool(
    db: AsyncSession,
    *,
    site_id: int,
    product_id: int,
    sku_id: Optional[int] = None,
    activity_session_id: Optional[int] = None,
    rental_asset_id: Optional[int] = None,
) -> Optional[InventoryPool]:
    """查询当前售卖单元命中的 active 库存池。"""
    target_conditions = []
    if product_id:
        target_conditions.append(InventoryPoolBinding.product_id == product_id)
    if sku_id:
        target_conditions.append(InventoryPoolBinding.sku_id == sku_id)
    if activity_session_id:
        target_conditions.append(InventoryPoolBinding.activity_session_id == activity_session_id)
    if rental_asset_id:
        target_conditions.append(InventoryPoolBinding.rental_asset_id == rental_asset_id)
    if not target_conditions:
        return None

    result = await db.execute(
        select(InventoryPool)
        .join(InventoryPoolBinding, InventoryPoolBinding.inventory_pool_id == InventoryPool.id)
        .where(
            InventoryPool.site_id == site_id,
            InventoryPool.status == "active",
            InventoryPool.is_deleted.is_(False),
            InventoryPoolBinding.site_id == site_id,
            InventoryPoolBinding.status == "active",
            InventoryPoolBinding.is_deleted.is_(False),
            or_(*target_conditions),
        )
        .order_by(
            _binding_specificity_case(
                product_id=product_id,
                sku_id=sku_id,
                activity_session_id=activity_session_id,
                rental_asset_id=rental_asset_id,
            ).asc(),
            InventoryPoolBinding.priority.asc(),
            InventoryPoolBinding.id.asc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_declared_inventory_pool(
    db: AsyncSession,
    *,
    site_id: int,
    product_id: int,
    sku_id: Optional[int] = None,
    activity_session_id: Optional[int] = None,
    rental_asset_id: Optional[int] = None,
) -> Optional[InventoryPool]:
    """查询未删除显式绑定库存池，供 Admin 写保护与日历展示使用。"""
    target_conditions = []
    if product_id:
        target_conditions.append(InventoryPoolBinding.product_id == product_id)
    if sku_id:
        target_conditions.append(InventoryPoolBinding.sku_id == sku_id)
    if activity_session_id:
        target_conditions.append(InventoryPoolBinding.activity_session_id == activity_session_id)
    if rental_asset_id:
        target_conditions.append(InventoryPoolBinding.rental_asset_id == rental_asset_id)
    if not target_conditions:
        return None

    result = await db.execute(
        select(InventoryPool)
        .join(InventoryPoolBinding, InventoryPoolBinding.inventory_pool_id == InventoryPool.id)
        .where(
            InventoryPool.site_id == site_id,
            InventoryPool.is_deleted.is_(False),
            InventoryPoolBinding.site_id == site_id,
            InventoryPoolBinding.is_deleted.is_(False),
            or_(*target_conditions),
        )
        .order_by(
            _binding_specificity_case(
                product_id=product_id,
                sku_id=sku_id,
                activity_session_id=activity_session_id,
                rental_asset_id=rental_asset_id,
            ).asc(),
            InventoryPoolBinding.priority.asc(),
            InventoryPoolBinding.id.asc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def lock_pool_inventory(
    db: AsyncSession,
    *,
    pool_id: int,
    quantity: int,
) -> InventoryPool:
    """锁定共享库存池库存。"""
    result = await db.execute(
        select(InventoryPool)
        .where(
            InventoryPool.id == pool_id,
            InventoryPool.status == "active",
            InventoryPool.is_deleted.is_(False),
        )
        .with_for_update()
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": 40404, "message": "库存池不存在或未启用"})
    try:
        validate_pool_availability(pool, required_quantity=quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": 40901, "message": str(exc)}) from exc

    pool.available -= quantity
    pool.locked += quantity
    await db.flush()
    return pool


async def release_pool_inventory(
    db: AsyncSession,
    *,
    pool_id: int,
    quantity: int,
) -> Optional[InventoryPool]:
    """释放共享库存池锁定库存。"""
    result = await db.execute(
        select(InventoryPool)
        .where(InventoryPool.id == pool_id, InventoryPool.is_deleted.is_(False))
        .with_for_update()
    )
    pool = result.scalar_one_or_none()
    if not pool:
        return None
    try:
        validate_pool_locked(pool, required_quantity=quantity)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40903, "message": str(exc)},
        ) from exc
    pool.locked -= quantity
    pool.available += quantity
    await db.flush()
    return pool


async def confirm_pool_sell(
    db: AsyncSession,
    *,
    pool_id: int,
    quantity: int,
) -> Optional[InventoryPool]:
    """共享库存池锁定转已售。"""
    result = await db.execute(
        select(InventoryPool)
        .where(InventoryPool.id == pool_id, InventoryPool.is_deleted.is_(False))
        .with_for_update()
    )
    pool = result.scalar_one_or_none()
    if not pool:
        return None
    try:
        validate_pool_locked(pool, required_quantity=quantity)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40903, "message": str(exc)},
        ) from exc
    pool.locked -= quantity
    pool.sold += quantity
    await db.flush()
    return pool


async def refund_pool_inventory(
    db: AsyncSession,
    *,
    pool_id: int,
    quantity: int,
) -> Optional[InventoryPool]:
    """共享库存池退款回补可用库存。"""
    result = await db.execute(
        select(InventoryPool)
        .where(InventoryPool.id == pool_id, InventoryPool.is_deleted.is_(False))
        .with_for_update()
    )
    pool = result.scalar_one_or_none()
    if not pool:
        return None
    sold = int(getattr(pool, "sold", 0) or 0)
    if sold < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40903, "message": f"共享库存已售不足，已售: {sold}, 需要回补: {quantity}"},
        )
    pool.sold -= quantity
    pool.available += quantity
    await db.flush()
    return pool


async def adjust_inventory_pool(
    db: AsyncSession,
    *,
    site_id: int,
    pool_id: int,
    mode: str,
    total: Optional[int] = None,
    delta: Optional[int] = None,
    pool_status: Optional[str] = None,
) -> dict[str, Any]:
    """安全调整共享库存池。

    人工调整只允许改总量或状态，locked/sold 由订单状态机维护；
    available 始终按 total - locked - sold 重新计算。
    """
    result = await db.execute(
        select(InventoryPool)
        .where(
            InventoryPool.id == pool_id,
            InventoryPool.site_id == site_id,
            InventoryPool.is_deleted.is_(False),
        )
        .with_for_update()
    )
    pool = result.scalar_one_or_none()
    if pool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="库存池不存在")

    before = {
        "total": pool.total,
        "available": pool.available,
        "locked": pool.locked,
        "sold": pool.sold,
        "status": pool.status,
    }

    if mode == "set_total":
        if total is None:
            raise HTTPException(status_code=400, detail="set_total 需要提供 total")
        next_total = int(total)
        next_available = next_total - int(pool.locked or 0) - int(pool.sold or 0)
        try:
            validate_pool_numbers(
                total=next_total,
                available=next_available,
                locked=int(pool.locked or 0),
                sold=int(pool.sold or 0),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        pool.total = next_total
        pool.available = next_available
    elif mode == "adjust_total":
        if delta is None:
            raise HTTPException(status_code=400, detail="adjust_total 需要提供 delta")
        next_total = int(pool.total or 0) + int(delta)
        next_available = next_total - int(pool.locked or 0) - int(pool.sold or 0)
        try:
            validate_pool_numbers(
                total=next_total,
                available=next_available,
                locked=int(pool.locked or 0),
                sold=int(pool.sold or 0),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        pool.total = next_total
        pool.available = next_available
    elif mode == "set_status":
        if pool_status is None:
            raise HTTPException(status_code=400, detail="set_status 需要提供 status")
    else:
        raise HTTPException(status_code=400, detail="mode 只能为 set_total/adjust_total/set_status")

    if pool_status is not None:
        if pool_status not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="库存池状态只能为 active/inactive")
        pool.status = pool_status

    await db.flush()
    after = {
        "total": pool.total,
        "available": pool.available,
        "locked": pool.locked,
        "sold": pool.sold,
        "status": pool.status,
    }
    return {"pool": pool, "before": before, "after": after}
