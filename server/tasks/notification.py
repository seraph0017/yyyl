"""
通知相关定时任务

17. task_trip_remind — 行程提醒（每天18点）
18. task_activity_start_remind — 活动开始提醒（每分钟）
19. task_refund_approval_timeout — 退款审批超时提醒（每2小时）
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from celery_app import celery_app
from models.notification import Notification
from models.order import Order, OrderItem, Ticket
from tasks.helpers import get_sync_db, task_monitor

logger = logging.getLogger("celery.tasks.notification")


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_trip_remind(self):
    """行程提醒：扫描明天有预定的用户，发送入营提醒

    逻辑：
    - 扫描电子票 verify_date = tomorrow 且 verify_status = 'pending'
    - 按用户去重，发送站内通知
    - 幂等性：Notification 表 (user_id, type, related_id) 去重
    """
    tomorrow = date.today() + timedelta(days=1)
    reminded = 0

    with get_sync_db() as db:
        tickets = db.execute(
            select(Ticket).where(
                Ticket.verify_date == tomorrow,
                Ticket.verify_status == "pending",
                Ticket.is_deleted.is_(False),
            )
        ).scalars().all()

        # 按用户去重
        user_ticket_map: dict[int, list] = {}
        for ticket in tickets:
            user_ticket_map.setdefault(ticket.user_id, []).append(ticket)

        for user_id, user_tickets in user_ticket_map.items():
            try:
                # 去重检查
                existing = db.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.type == "trip_remind",
                        Notification.related_id == str(tomorrow),
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                ticket_count = len(user_tickets)
                notification = Notification(
                    user_id=user_id,
                    type="trip_remind",
                    title="明日行程提醒",
                    content=f"您明天（{tomorrow}）有{ticket_count}张电子票待使用，记得按时入营哦~",
                    related_id=str(tomorrow),
                    related_type="trip",
                )
                db.add(notification)
                reminded += 1

                # TODO: 发送微信订阅消息

            except Exception as e:
                logger.error(f"[行程提醒] 失败: user_id={user_id}, error={e}")

    return {"reminded": reminded}


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_activity_start_remind(self):
    """活动开始提醒：扫描即将开始的活动，通知已购票用户

    逻辑：
    - 扫描即将在60分钟内开票的商品
    - 查找对应已支付订单的用户
    - 发送"活动即将开始"通知
    """
    now = datetime.now(timezone.utc)
    remind_60min = now + timedelta(minutes=60)
    remind_10min = now + timedelta(minutes=10)
    reminded = 0

    with get_sync_db() as db:
        from models.product import Product

        # 60分钟内开始的商品
        upcoming = db.execute(
            select(Product).where(
                Product.sale_start_at.between(now, remind_60min),
                Product.status == "on_sale",
                Product.is_deleted.is_(False),
            )
        ).scalars().all()

        for product in upcoming:
            # 查找已支付该商品的订单
            order_items = db.execute(
                select(OrderItem).where(
                    OrderItem.product_id == product.id,
                )
            ).scalars().all()

            order_ids = {oi.order_id for oi in order_items}
            if not order_ids:
                continue

            orders = db.execute(
                select(Order).where(
                    Order.id.in_(order_ids),
                    Order.status == "paid",
                    Order.is_deleted.is_(False),
                )
            ).scalars().all()

            for order in orders:
                try:
                    # 判断是60分钟档还是10分钟档
                    is_urgent = (
                        product.sale_start_at
                        and product.sale_start_at <= remind_10min
                    )
                    template_type = "activity_urgent" if is_urgent else "activity_remind"

                    # 去重（四元组）
                    related_key = f"{product.id}:{order.user_id}:{template_type}"
                    existing = db.execute(
                        select(Notification).where(
                            Notification.user_id == order.user_id,
                            Notification.type == template_type,
                            Notification.related_id == related_key,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        continue

                    title = "活动马上开始！" if is_urgent else "活动即将开始"
                    content = (
                        f"您报名的「{product.name}」即将开始，请提前做好准备"
                        if is_urgent
                        else f"您报名的「{product.name}」将在1小时内开始"
                    )

                    notification = Notification(
                        user_id=order.user_id,
                        type=template_type,
                        title=title,
                        content=content,
                        related_id=related_key,
                        related_type="product",
                    )
                    db.add(notification)
                    reminded += 1

                except Exception as e:
                    logger.error(f"[活动提醒] 失败: order_id={order.id}, error={e}")

    return {"reminded": reminded}


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_refund_approval_timeout(self):
    """退款审批超时提醒：退款申请超24小时未处理，通知管理员

    逻辑：
    - 扫描 status='refund_pending' 超过24小时的订单
    - 同一订单每24小时最多提醒一次
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=24)
    alerted = 0

    with get_sync_db() as db:
        pending_refunds = db.execute(
            select(Order).where(
                Order.status == "refund_pending",
                Order.updated_at <= threshold,
                Order.is_deleted.is_(False),
            )
        ).scalars().all()

        for order in pending_refunds:
            try:
                existing = db.execute(
                    select(Notification).where(
                        Notification.type == "refund_approval_timeout",
                        Notification.related_id == str(order.id),
                        Notification.created_at >= now - timedelta(hours=24),
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                notification = Notification(
                    user_id=0,  # 系统通知
                    type="refund_approval_timeout",
                    title="退款审批超时",
                    content=(
                        f"订单 {order.order_no} 的退款申请已超24小时未处理，"
                        f"请尽快审批"
                    ),
                    related_id=str(order.id),
                    related_type="order",
                )
                db.add(notification)
                alerted += 1

            except Exception as e:
                logger.error(f"[审批超时] 失败: order_id={order.id}, error={e}")

    return {"alerted": alerted}
