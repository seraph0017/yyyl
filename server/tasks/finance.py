"""
财务相关定时任务

10. task_income_confirm — 收入确认（每天3点）
11. task_deposit_timeout_alert — 押金超时提醒（每天10点）
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from celery_app import celery_app
from models.finance import DepositRecord, FinanceAccount, FinanceTransaction
from models.notification import Notification
from models.order import Order
from tasks.helpers import get_sync_db, task_monitor
from utils.helpers import generate_transaction_no

logger = logging.getLogger("celery.tasks.finance")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_income_confirm(self):
    """收入确认：已验票订单服务日期过N天后，收入从待确认转可提现

    逻辑：
    - 扫描 FinanceTransaction 中 status='pending' 且创建超过1天的记录
    - 转为 confirmed，更新 FinanceAccount pending→available
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=1)
    confirmed = 0

    with get_sync_db() as db:
        pending_txs = db.execute(
            select(FinanceTransaction).where(
                FinanceTransaction.status == "pending",
                FinanceTransaction.type == "income",
                FinanceTransaction.created_at <= threshold,
                FinanceTransaction.is_deleted.is_(False),
            )
        ).scalars().all()

        for tx in pending_txs:
            try:
                tx.status = "confirmed"

                # 更新财务账户
                account = db.execute(
                    select(FinanceAccount).where(
                        FinanceAccount.site_id == tx.site_id
                    )
                ).scalar_one_or_none()

                if account:
                    move_amount = tx.amount
                    account.pending_amount = max(
                        Decimal("0"), account.pending_amount - move_amount
                    )
                    account.available_amount += move_amount

                confirmed += 1
                logger.info(f"[收入确认] tx_id={tx.id}, amount={tx.amount}")

            except Exception as e:
                logger.error(f"[收入确认] 失败: tx_id={tx.id}, error={e}")

    return {"confirmed": confirmed}


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_deposit_timeout_alert(self):
    """押金超时提醒：装备租赁过3天未归还，通知管理员

    逻辑：
    - 扫描 DepositRecord 中 status='held' 且创建超过3天的记录
    - 通过站内通知提醒管理员
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=3)
    alerted = 0

    with get_sync_db() as db:
        overdue_deposits = db.execute(
            select(DepositRecord).where(
                DepositRecord.status == "held",
                DepositRecord.created_at <= threshold,
                DepositRecord.is_deleted.is_(False),
            )
        ).scalars().all()

        for deposit in overdue_deposits:
            try:
                # 去重：同一押金记录每24小时最多提醒一次
                existing = db.execute(
                    select(Notification).where(
                        Notification.type == "deposit_timeout_alert",
                        Notification.related_id == str(deposit.id),
                        Notification.created_at >= now - timedelta(hours=24),
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                # 发通知给管理员（user_id=0 表示系统通知）
                notification = Notification(
                    user_id=0,
                    type="deposit_timeout_alert",
                    title="押金超时未归还",
                    content=(
                        f"押金记录 #{deposit.id}（订单 order_id={deposit.order_id}）"
                        f"已超过3天未归还，金额: ¥{deposit.deposit_amount}"
                    ),
                    related_id=str(deposit.id),
                    related_type="deposit",
                )
                db.add(notification)
                alerted += 1

            except Exception as e:
                logger.error(f"[押金超时] 失败: deposit_id={deposit.id}, error={e}")

    return {"alerted": alerted}
