"""
库存相关定时任务

1. task_auto_release_tickets — 定时开票（每分钟）
2. task_inventory_auto_release — 库存超时释放（每分钟）
3. task_inventory_consistency_check — 库存一致性校验（每10分钟）
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from celery_app import celery_app
from models.product import Inventory, InventoryLog, Product
from models.order import Order, OrderItem
from tasks.helpers import get_sync_db, get_sync_redis, task_monitor

logger = logging.getLogger("celery.tasks.inventory")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
@task_monitor
def task_auto_release_tickets(self):
    """定时开票：扫描到达开票时间的商品，自动上架

    逻辑：
    - 扫描 Product 表中 sale_start_at ≤ now() 且 status = 'draft' 的商品
    - 更新状态为 on_sale
    - 幂等性：基于 status='draft' 条件保证不会重复处理
    """
    now = datetime.now(timezone.utc)
    count = 0

    with get_sync_db() as db:
        products = db.execute(
            select(Product).where(
                Product.sale_start_at <= now,
                Product.status == "draft",
                Product.is_deleted.is_(False),
            )
        ).scalars().all()

        for product in products:
            product.status = "on_sale"
            count += 1
            logger.info(f"[开票] 商品自动上架: id={product.id}, name={product.name}")

    r = get_sync_redis()
    if count > 0:
        # 清除商品列表缓存
        for key in r.scan_iter("cache:products:*"):
            r.delete(key)

    return {"released": count}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
@task_monitor
def task_inventory_auto_release(self):
    """库存超时释放：扫描超时未支付订单，取消并释放库存

    逻辑：
    - 扫描 Order 中 status='pending_payment' 且 expire_at ≤ now() 的订单
    - 逐单处理：取消订单 → 恢复 Inventory available → 回补 Redis → 记录 InventoryLog
    - 单条失败不影响其他订单，失败单下轮重新扫到
    """
    now = datetime.now(timezone.utc)
    cancelled = 0
    errors = 0

    with get_sync_db() as db:
        expired_orders = db.execute(
            select(Order).where(
                Order.status == "pending_payment",
                Order.expire_at <= now,
                Order.is_deleted.is_(False),
            )
        ).scalars().all()

        for order in expired_orders:
            try:
                # 取消订单
                order.status = "cancelled"
                order.remark = "系统自动取消：支付超时"

                # 释放库存
                items = db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id)
                ).scalars().all()

                for item in items:
                    if item.date:
                        inv = db.execute(
                            select(Inventory).where(
                                Inventory.product_id == item.product_id,
                                Inventory.date == item.date,
                                Inventory.is_deleted.is_(False),
                            )
                        ).scalar_one_or_none()

                        if inv and inv.locked >= item.quantity:
                            inv.locked -= item.quantity
                            inv.available += item.quantity

                            log = InventoryLog(
                                inventory_id=inv.id,
                                change_type="unlock",
                                quantity=item.quantity,
                                order_id=order.id,
                                remark=f"超时自动释放 order_id={order.id}",
                            )
                            db.add(log)

                            # 回补 Redis 秒杀库存（如果有）
                            r = get_sync_redis()
                            stock_key = f"seckill_stock:{item.product_id}:{item.date}"
                            if r.exists(stock_key):
                                r.incrby(stock_key, item.quantity)
                                # 清除售罄标记
                                sold_out_key = f"seckill_sold_out:{item.product_id}"
                                r.delete(sold_out_key)

                db.flush()
                cancelled += 1
                logger.info(f"[库存释放] 订单超时取消: order_id={order.id}")

            except Exception as e:
                errors += 1
                logger.error(f"[库存释放] 处理失败: order_id={order.id}, error={e}")
                db.rollback()

    return {"cancelled": cancelled, "errors": errors}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_inventory_consistency_check(self):
    """库存一致性校验：对比 Redis 与 DB 库存，不一致以 DB 为准

    逻辑：
    - 扫描 Redis 中的 seckill_stock:* 键
    - 对比 DB Inventory 表的 available 值
    - 不一致时以 DB 为准覆盖 Redis 并记录告警
    """
    r = get_sync_redis()
    fixed = 0

    with get_sync_db() as db:
        for key in r.scan_iter("seckill_stock:*"):
            parts = key.split(":")
            if len(parts) != 3:
                continue

            product_id = int(parts[1])
            inv_date = parts[2]

            redis_stock = int(r.get(key) or 0)

            inv = db.execute(
                select(Inventory).where(
                    Inventory.product_id == product_id,
                    Inventory.date == inv_date,
                    Inventory.is_deleted.is_(False),
                )
            ).scalar_one_or_none()

            if inv is None:
                continue

            db_available = inv.available
            if redis_stock != db_available:
                logger.warning(
                    f"[一致性] 库存不一致: product={product_id}, date={inv_date}, "
                    f"redis={redis_stock}, db={db_available}, 已修正为DB值"
                )
                r.set(key, db_available)
                fixed += 1

    return {"checked": True, "fixed": fixed}
