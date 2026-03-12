"""
库存服务

- query_inventory：库存查询（按商品/日期范围）
- lock_inventory：库存锁定（配合Redis分布式锁）
- release_inventory：库存释放
- batch_open_inventory：批量开启库存
- update_inventory：更新单个库存记录
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.product import Inventory, InventoryLog
from redis_client import get_redis

logger = logging.getLogger(__name__)


async def query_inventory(
    db: AsyncSession,
    *,
    product_id: Optional[int] = None,
    sku_id: Optional[int] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    inv_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Inventory], int]:
    """库存查询

    Args:
        db: 数据库会话
        product_id: 商品ID
        sku_id: SKU ID
        date_start: 起始日期
        date_end: 结束日期
        inv_status: 库存状态
        page: 页码
        page_size: 每页数量

    Returns:
        (库存列表, 总数)
    """
    query = select(Inventory).where(Inventory.is_deleted.is_(False))

    if product_id:
        query = query.where(Inventory.product_id == product_id)
    if sku_id:
        query = query.where(Inventory.sku_id == sku_id)
    if date_start:
        query = query.where(Inventory.date >= date_start)
    if date_end:
        query = query.where(Inventory.date <= date_end)
    if inv_status:
        query = query.where(Inventory.status == inv_status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序和分页
    query = query.order_by(Inventory.date.asc(), Inventory.product_id.asc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    inventories = list(result.scalars().all())

    return inventories, total


async def lock_inventory(
    db: AsyncSession,
    product_id: int,
    inv_date: date,
    quantity: int,
    order_id: int,
    sku_id: Optional[int] = None,
    time_slot: Optional[str] = None,
) -> Inventory:
    """锁定库存

    使用 Redis 分布式锁 + 数据库乐观更新

    Args:
        db: 数据库会话
        product_id: 商品ID
        inv_date: 日期
        quantity: 锁定数量
        order_id: 订单ID
        sku_id: SKU ID
        time_slot: 场次

    Returns:
        更新后的 Inventory

    Raises:
        HTTPException 40901: 库存不足
        HTTPException 40404: 库存记录不存在
    """
    redis = get_redis()
    lock_key = f"inv_lock:{product_id}:{inv_date}:{sku_id or 0}:{time_slot or ''}"

    # Redis 分布式锁（5秒超时）
    lock_acquired = await redis.set(lock_key, "1", ex=5, nx=True)
    if not lock_acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": "库存操作冲突，请稍后重试"},
        )

    try:
        # 查询库存记录
        query = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.date == inv_date,
            Inventory.is_deleted.is_(False),
            Inventory.status == "open",
        )
        if sku_id:
            query = query.where(Inventory.sku_id == sku_id)
        if time_slot:
            query = query.where(Inventory.time_slot == time_slot)

        result = await db.execute(query)
        inv = result.scalar_one_or_none()

        if inv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 40404, "message": "库存记录不存在或已关闭"},
            )

        if inv.available < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 40901, "message": f"库存不足，可用: {inv.available}, 需要: {quantity}"},
            )

        # 锁定库存
        inv.available -= quantity
        inv.locked += quantity

        # 写入变动日志
        log = InventoryLog(
            inventory_id=inv.id,
            change_type="lock",
            quantity=quantity,
            order_id=order_id,
            remark=f"订单锁定 order_id={order_id}",
        )
        db.add(log)
        await db.flush()

        return inv

    finally:
        await redis.delete(lock_key)


async def release_inventory(
    db: AsyncSession,
    product_id: int,
    inv_date: date,
    quantity: int,
    order_id: int,
    sku_id: Optional[int] = None,
    time_slot: Optional[str] = None,
) -> Optional[Inventory]:
    """释放锁定的库存

    Args:
        db: 数据库会话
        product_id: 商品ID
        inv_date: 日期
        quantity: 释放数量
        order_id: 订单ID
        sku_id: SKU ID
        time_slot: 场次

    Returns:
        更新后的 Inventory 或 None
    """
    query = select(Inventory).where(
        Inventory.product_id == product_id,
        Inventory.date == inv_date,
        Inventory.is_deleted.is_(False),
    )
    if sku_id:
        query = query.where(Inventory.sku_id == sku_id)
    if time_slot:
        query = query.where(Inventory.time_slot == time_slot)

    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if inv is None:
        logger.warning(
            f"[库存] 释放失败，记录不存在: product={product_id}, date={inv_date}"
        )
        return None

    release_qty = min(quantity, inv.locked)
    inv.locked -= release_qty
    inv.available += release_qty

    log = InventoryLog(
        inventory_id=inv.id,
        change_type="unlock",
        quantity=release_qty,
        order_id=order_id,
        remark=f"订单释放 order_id={order_id}",
    )
    db.add(log)
    await db.flush()

    return inv


async def confirm_sell(
    db: AsyncSession,
    product_id: int,
    inv_date: date,
    quantity: int,
    order_id: int,
    sku_id: Optional[int] = None,
    time_slot: Optional[str] = None,
) -> Optional[Inventory]:
    """确认售出（锁定→已售）

    Args:
        db: 数据库会话
        product_id: 商品ID
        inv_date: 日期
        quantity: 售出数量
        order_id: 订单ID

    Returns:
        更新后的 Inventory 或 None
    """
    query = select(Inventory).where(
        Inventory.product_id == product_id,
        Inventory.date == inv_date,
        Inventory.is_deleted.is_(False),
    )
    if sku_id:
        query = query.where(Inventory.sku_id == sku_id)
    if time_slot:
        query = query.where(Inventory.time_slot == time_slot)

    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if inv is None:
        return None

    sell_qty = min(quantity, inv.locked)
    inv.locked -= sell_qty
    inv.sold += sell_qty

    log = InventoryLog(
        inventory_id=inv.id,
        change_type="sell",
        quantity=sell_qty,
        order_id=order_id,
        remark=f"订单确认 order_id={order_id}",
    )
    db.add(log)
    await db.flush()

    return inv


async def batch_open_inventory(
    db: AsyncSession,
    product_ids: List[int],
    date_start: date,
    date_end: date,
    total_per_day: int,
    operator_id: int,
    remark: Optional[str] = None,
) -> int:
    """批量开启库存

    Args:
        db: 数据库会话
        product_ids: 商品ID列表
        date_start: 起始日期
        date_end: 结束日期
        total_per_day: 每日库存总量
        operator_id: 操作人
        remark: 备注

    Returns:
        创建/更新的库存记录数
    """
    count = 0
    current = date_start
    while current <= date_end:
        for pid in product_ids:
            # 检查是否已有记录
            result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == pid,
                    Inventory.date == current,
                    Inventory.is_deleted.is_(False),
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 更新现有记录
                existing.total = total_per_day
                existing.available = total_per_day - existing.locked - existing.sold
                existing.status = "open"
            else:
                inv = Inventory(
                    product_id=pid,
                    date=current,
                    total=total_per_day,
                    available=total_per_day,
                    locked=0,
                    sold=0,
                    status="open",
                )
                db.add(inv)

            count += 1

        current += timedelta(days=1)

    await db.flush()
    logger.info(
        f"[库存] 批量开启: products={product_ids}, {date_start}~{date_end}, "
        f"total={total_per_day}, count={count}, operator={operator_id}"
    )
    return count


async def update_inventory_record(
    db: AsyncSession,
    inventory_id: int,
    *,
    total: Optional[int] = None,
    inv_status: Optional[str] = None,
    operator_id: Optional[int] = None,
    remark: Optional[str] = None,
) -> Inventory:
    """更新库存记录

    Args:
        db: 数据库会话
        inventory_id: 库存ID
        total: 新的总库存
        inv_status: 新的状态
        operator_id: 操作人
        remark: 备注

    Returns:
        更新后的 Inventory
    """
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.is_deleted.is_(False),
        )
    )
    inv = result.scalar_one_or_none()

    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40404, "message": "库存记录不存在"},
        )

    old_total = inv.total

    if total is not None:
        diff = total - inv.total
        inv.total = total
        inv.available = max(0, inv.available + diff)

        log = InventoryLog(
            inventory_id=inv.id,
            change_type="manual_adjust",
            quantity=diff,
            operator_id=operator_id,
            remark=remark or f"手动调整: {old_total} -> {total}",
        )
        db.add(log)

    if inv_status is not None:
        inv.status = inv_status

    await db.flush()
    return inv
