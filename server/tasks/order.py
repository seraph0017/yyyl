"""
订单相关定时任务

3. task_cancel_expired_orders — 超时取消（每分钟，与库存释放协同）
4. task_auto_complete_orders — 自动完成（每天凌晨2点）
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from celery_app import celery_app
from models.order import Order, Ticket
from services import settlement_service
from tasks.helpers import get_sync_db, task_monitor

logger = logging.getLogger("celery.tasks.order")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
@task_monitor
def task_cancel_expired_orders(self):
    """超时取消订单（与 task_inventory_auto_release 协同）

    逻辑：
    - 普通订单超时30分钟，秒杀订单超时5分钟
    - 超时后取消订单 → 释放库存 → 发送取消通知（站内信）
    - 此任务侧重于发通知和写站内信，库存释放由 inventory 任务处理
    """
    now = datetime.now(timezone.utc)
    notified = 0

    with get_sync_db() as db:
        # 查找刚被超时取消的订单（可能由 inventory_auto_release 取消）
        # 查找最近5分钟内被系统取消、但尚未发通知的订单
        recently_cancelled = db.execute(
            select(Order).where(
                Order.status == "cancelled",
                Order.remark.like("%系统自动取消%"),
                Order.updated_at >= now - timedelta(minutes=5),
                Order.is_deleted.is_(False),
            )
        ).scalars().all()

        for order in recently_cancelled:
            try:
                from models.notification import Notification

                # 检查是否已发过通知（幂等）
                existing = db.execute(
                    select(Notification).where(
                        Notification.user_id == order.user_id,
                        Notification.type == "order_cancelled",
                        Notification.related_id == str(order.id),
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                # 创建站内通知
                notification = Notification(
                    user_id=order.user_id,
                    type="order_cancelled",
                    title="订单已取消",
                    content=f"您的订单 {order.order_no} 因支付超时已自动取消",
                    related_id=str(order.id),
                    related_type="order",
                )
                db.add(notification)
                notified += 1

            except Exception as e:
                logger.error(f"[订单通知] 失败: order_id={order.id}, error={e}")

    return {"notified": notified}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_auto_complete_orders(self):
    """自动完成订单：验票后N天自动流转为 completed，收入确认

    逻辑：
    - 扫描 status='verified' 且验票日期已过1天的订单
    - 流转为 completed
    - 通过 settlement_service 幂等结算到可提现账户
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=1)
    completed = 0

    with get_sync_db() as db:
        orders = db.execute(
            select(Order).where(
                Order.status == "verified",
                Order.is_deleted.is_(False),
            )
        ).scalars().all()

        for order in orders:
            try:
                # 检查所有票是否都已验票且过了1天
                tickets = db.execute(
                    select(Ticket).where(
                        Ticket.order_id == order.id,
                        Ticket.is_deleted.is_(False),
                    )
                ).scalars().all()

                if not tickets:
                    continue

                all_verified = all(
                    t.verify_status == "verified"
                    and t.verified_at
                    and t.verified_at <= threshold
                    for t in tickets
                )

                if not all_verified:
                    continue

                # 订单完成
                order.status = "completed"

                settlement_service.settle_completed_order_sync(
                    db,
                    order,
                    trigger_type="auto",
                )
                completed += 1
                logger.info(f"[订单完成] order_id={order.id}")

            except Exception as e:
                logger.error(f"[订单完成] 失败: order_id={order.id}, error={e}")

    return {"completed": completed}
