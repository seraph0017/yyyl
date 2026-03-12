"""
会员相关定时任务

5. task_annual_card_expire — 年卡到期处理（每天0点）
6. task_times_card_expire — 次数卡到期处理（每天0点）
7. task_annual_card_expire_remind — 年卡到期提醒（每天9点）
8. task_times_card_expire_remind — 次数卡到期提醒（每天9点）
9. task_points_expire — 积分过期（每天1点）
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select

from celery_app import celery_app
from models.member import AnnualCard, TimesCard, PointsRecord
from models.notification import Notification
from models.user import User
from tasks.helpers import get_sync_db, task_monitor

logger = logging.getLogger("celery.tasks.member")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_annual_card_expire(self):
    """年卡到期处理：扫描过期年卡，更新状态为 expired"""
    today = date.today()
    expired_count = 0

    with get_sync_db() as db:
        cards = db.execute(
            select(AnnualCard).where(
                AnnualCard.end_date < today,
                AnnualCard.status == "active",
                AnnualCard.is_deleted.is_(False),
            )
        ).scalars().all()

        for card in cards:
            card.status = "expired"
            expired_count += 1
            logger.info(f"[年卡] 过期处理: card_id={card.id}, user_id={card.user_id}")

    return {"expired": expired_count}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_times_card_expire(self):
    """次数卡到期处理：扫描过期次数卡，更新状态为 expired"""
    today = date.today()
    expired_count = 0

    with get_sync_db() as db:
        cards = db.execute(
            select(TimesCard).where(
                TimesCard.end_date < today,
                TimesCard.status == "active",
                TimesCard.is_deleted.is_(False),
            )
        ).scalars().all()

        for card in cards:
            card.status = "expired"
            expired_count += 1
            logger.info(f"[次数卡] 过期处理: card_id={card.id}, user_id={card.user_id}")

    return {"expired": expired_count}


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_annual_card_expire_remind(self):
    """年卡到期提醒：到期前7天和1天推送提醒"""
    today = date.today()
    remind_dates = [today + timedelta(days=7), today + timedelta(days=1)]
    reminded = 0

    with get_sync_db() as db:
        for remind_date in remind_dates:
            days_left = (remind_date - today).days

            cards = db.execute(
                select(AnnualCard).where(
                    AnnualCard.end_date == remind_date,
                    AnnualCard.status == "active",
                    AnnualCard.is_deleted.is_(False),
                )
            ).scalars().all()

            for card in cards:
                # 去重检查
                existing = db.execute(
                    select(Notification).where(
                        Notification.user_id == card.user_id,
                        Notification.type == "annual_card_expire_remind",
                        Notification.related_id == str(card.id),
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                notification = Notification(
                    user_id=card.user_id,
                    type="annual_card_expire_remind",
                    title="年卡即将到期",
                    content=f"您的年卡将在{days_left}天后到期（{remind_date}），请及时续费",
                    related_id=str(card.id),
                    related_type="annual_card",
                )
                db.add(notification)
                reminded += 1

                # TODO: 发送微信订阅消息

    return {"reminded": reminded}


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_times_card_expire_remind(self):
    """次数卡到期提醒：到期前7天和1天推送提醒"""
    today = date.today()
    remind_dates = [today + timedelta(days=7), today + timedelta(days=1)]
    reminded = 0

    with get_sync_db() as db:
        for remind_date in remind_dates:
            days_left = (remind_date - today).days

            cards = db.execute(
                select(TimesCard).where(
                    TimesCard.end_date == remind_date,
                    TimesCard.status == "active",
                    TimesCard.is_deleted.is_(False),
                )
            ).scalars().all()

            for card in cards:
                existing = db.execute(
                    select(Notification).where(
                        Notification.user_id == card.user_id,
                        Notification.type == "times_card_expire_remind",
                        Notification.related_id == str(card.id),
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                notification = Notification(
                    user_id=card.user_id,
                    type="times_card_expire_remind",
                    title="次数卡即将到期",
                    content=f"您的次数卡将在{days_left}天后到期，剩余{card.remaining_times}次未使用",
                    related_id=str(card.id),
                    related_type="times_card",
                )
                db.add(notification)
                reminded += 1

    return {"reminded": reminded}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_points_expire(self):
    """积分过期：扫描过期积分记录，扣减用户积分余额

    逻辑：
    - 扫描 PointsRecord 中 expires_at < today 且 change_type='earn' 的未过期记录
    - 扣减对应用户的 points_balance
    - 记录积分变动日志
    """
    today = date.today()
    expired_count = 0

    with get_sync_db() as db:
        # 查找有 expires_at 且已过期的积分记录
        records = db.execute(
            select(PointsRecord).where(
                PointsRecord.expires_at < today,
                PointsRecord.change_type == "earn",
                PointsRecord.is_expired.is_(False),
                PointsRecord.is_deleted.is_(False),
            )
        ).scalars().all()

        for record in records:
            try:
                user = db.execute(
                    select(User).where(User.id == record.user_id)
                ).scalar_one_or_none()

                if user is None:
                    continue

                expire_amount = record.change_amount
                if expire_amount <= 0:
                    continue

                # 扣减积分（不低于0）
                actual_deduct = min(expire_amount, user.points_balance)
                user.points_balance -= actual_deduct

                # 标记已过期
                record.is_expired = True

                # 记录变动
                expire_log = PointsRecord(
                    user_id=record.user_id,
                    change_amount=-actual_deduct,
                    balance_after=user.points_balance,
                    change_type="expire",
                    reason=f"积分过期（原记录ID: {record.id}）",
                )
                db.add(expire_log)
                expired_count += 1

            except Exception as e:
                logger.error(f"[积分过期] 失败: record_id={record.id}, error={e}")

    return {"expired": expired_count}
