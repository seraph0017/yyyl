"""
数据统计相关定时任务

12. task_dashboard_aggregate — Dashboard数据聚合（每5分钟）
13. task_heatmap_calculate — 营位热力图（每天4点）
14. task_daily_report — 日报（每天5点）
15. task_weekly_report — 周报（每周一5点）
16. task_monthly_report — 月报（每月1日6点）
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from celery_app import celery_app
from models.admin import DailyReport, WeeklyReport, MonthlyReport
from models.finance import FinanceTransaction
from models.order import Order, Ticket
from models.product import Inventory
from models.user import User
from tasks.helpers import get_sync_db, get_sync_redis, task_monitor

logger = logging.getLogger("celery.tasks.stats")


class DecimalEncoder(json.JSONEncoder):
    """JSON 编码器，支持 Decimal 和 date"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_dashboard_aggregate(self):
    """Dashboard数据聚合：实时统计数据写入 Redis 缓存

    聚合内容：今日订单数、今日收入、在营人数、趋势图数据
    """
    r = get_sync_redis()
    today = date.today()

    with get_sync_db() as db:
        # 今日订单数
        today_orders = db.execute(
            select(func.count()).where(
                func.date(Order.created_at) == today,
                Order.is_deleted.is_(False),
            )
        ).scalar() or 0

        # 今日已支付订单数
        today_paid = db.execute(
            select(func.count()).where(
                func.date(Order.payment_time) == today,
                Order.payment_status == "paid",
                Order.is_deleted.is_(False),
            )
        ).scalar() or 0

        # 今日收入
        today_income = db.execute(
            select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
                func.date(Order.payment_time) == today,
                Order.payment_status == "paid",
                Order.is_deleted.is_(False),
            )
        ).scalar() or Decimal("0")

        # 今日在营人数（今天已验票的票数）
        today_verified = db.execute(
            select(func.count()).where(
                Ticket.verify_date == today,
                Ticket.verify_status == "verified",
                Ticket.is_deleted.is_(False),
            )
        ).scalar() or 0

        # 总用户数
        total_users = db.execute(
            select(func.count()).where(User.is_deleted.is_(False))
        ).scalar() or 0

        # 最近7天订单趋势
        trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_count = db.execute(
                select(func.count()).where(
                    func.date(Order.created_at) == d,
                    Order.is_deleted.is_(False),
                )
            ).scalar() or 0
            day_income = db.execute(
                select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
                    func.date(Order.payment_time) == d,
                    Order.payment_status == "paid",
                    Order.is_deleted.is_(False),
                )
            ).scalar() or Decimal("0")
            trend.append({
                "date": d.isoformat(),
                "orders": day_count,
                "income": float(day_income),
            })

    dashboard_data = {
        "today_orders": today_orders,
        "today_paid": today_paid,
        "today_income": float(today_income),
        "today_verified": today_verified,
        "total_users": total_users,
        "trend": trend,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    r.set(
        "dashboard:data",
        json.dumps(dashboard_data, cls=DecimalEncoder),
        ex=600,  # 10分钟过期
    )

    return {"aggregated": True}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_heatmap_calculate(self):
    """营位热力图：计算近30天各营位预定率"""
    r = get_sync_redis()
    today = date.today()
    start = today - timedelta(days=30)

    with get_sync_db() as db:
        inventories = db.execute(
            select(Inventory).where(
                Inventory.date >= start,
                Inventory.date <= today,
                Inventory.is_deleted.is_(False),
            )
        ).scalars().all()

        # 按商品聚合
        product_stats: dict[int, dict] = {}
        for inv in inventories:
            if inv.product_id not in product_stats:
                product_stats[inv.product_id] = {"total": 0, "sold": 0, "days": 0}
            stats = product_stats[inv.product_id]
            stats["total"] += inv.total
            stats["sold"] += inv.sold
            stats["days"] += 1

        heatmap = []
        for pid, stats in product_stats.items():
            rate = stats["sold"] / stats["total"] * 100 if stats["total"] > 0 else 0
            heatmap.append({
                "product_id": pid,
                "booking_rate": round(rate, 1),
                "total_capacity": stats["total"],
                "total_sold": stats["sold"],
                "days": stats["days"],
            })

    r.set(
        "dashboard:heatmap",
        json.dumps(heatmap),
        ex=90000,  # 25小时
    )

    return {"products": len(heatmap)}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_daily_report(self):
    """日报生成：统计前一天的数据"""
    yesterday = date.today() - timedelta(days=1)

    with get_sync_db() as db:
        # 检查是否已生成
        existing = db.execute(
            select(DailyReport).where(
                DailyReport.report_date == yesterday,
                DailyReport.site_id == 1,
            )
        ).scalar_one_or_none()

        # 统计数据
        order_count = db.execute(
            select(func.count()).where(
                func.date(Order.created_at) == yesterday,
                Order.is_deleted.is_(False),
            )
        ).scalar() or 0

        paid_count = db.execute(
            select(func.count()).where(
                func.date(Order.payment_time) == yesterday,
                Order.payment_status == "paid",
                Order.is_deleted.is_(False),
            )
        ).scalar() or 0

        total_income = db.execute(
            select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
                func.date(Order.payment_time) == yesterday,
                Order.payment_status == "paid",
                Order.is_deleted.is_(False),
            )
        ).scalar() or Decimal("0")

        refund_amount = db.execute(
            select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
                FinanceTransaction.type == "refund",
                func.date(FinanceTransaction.created_at) == yesterday,
            )
        ).scalar() or Decimal("0")

        new_users = db.execute(
            select(func.count()).where(
                func.date(User.created_at) == yesterday,
                User.is_deleted.is_(False),
            )
        ).scalar() or 0

        verified_count = db.execute(
            select(func.count()).where(
                Ticket.verify_date == yesterday,
                Ticket.verify_status == "verified",
                Ticket.is_deleted.is_(False),
            )
        ).scalar() or 0

        report_data = {
            "order_count": order_count,
            "paid_count": paid_count,
            "total_income": float(total_income),
            "refund_amount": float(refund_amount),
            "new_users": new_users,
            "verified_count": verified_count,
        }

        if existing:
            existing.data = json.dumps(report_data, cls=DecimalEncoder)
        else:
            report = DailyReport(
                report_date=yesterday,
                site_id=1,
                data=json.dumps(report_data, cls=DecimalEncoder),
            )
            db.add(report)

    return {"date": yesterday.isoformat(), "data": report_data}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_weekly_report(self):
    """周报生成：聚合上周数据"""
    today = date.today()
    # 上周一到上周日
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    with get_sync_db() as db:
        existing = db.execute(
            select(WeeklyReport).where(
                WeeklyReport.report_date == last_monday,
                WeeklyReport.site_id == 1,
            )
        ).scalar_one_or_none()

        order_count = db.execute(
            select(func.count()).where(
                func.date(Order.created_at).between(last_monday, last_sunday),
                Order.is_deleted.is_(False),
            )
        ).scalar() or 0

        total_income = db.execute(
            select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
                func.date(Order.payment_time).between(last_monday, last_sunday),
                Order.payment_status == "paid",
                Order.is_deleted.is_(False),
            )
        ).scalar() or Decimal("0")

        report_data = {
            "week_start": last_monday.isoformat(),
            "week_end": last_sunday.isoformat(),
            "order_count": order_count,
            "total_income": float(total_income),
        }

        if existing:
            existing.data = json.dumps(report_data, cls=DecimalEncoder)
        else:
            report = WeeklyReport(
                report_date=last_monday,
                site_id=1,
                data=json.dumps(report_data, cls=DecimalEncoder),
            )
            db.add(report)

    return report_data


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
@task_monitor
def task_monthly_report(self):
    """月报生成：聚合上月数据"""
    today = date.today()
    # 上月第一天和最后一天
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    first_of_prev_month = last_of_prev_month.replace(day=1)

    with get_sync_db() as db:
        existing = db.execute(
            select(MonthlyReport).where(
                MonthlyReport.report_date == first_of_prev_month,
                MonthlyReport.site_id == 1,
            )
        ).scalar_one_or_none()

        order_count = db.execute(
            select(func.count()).where(
                func.date(Order.created_at).between(
                    first_of_prev_month, last_of_prev_month
                ),
                Order.is_deleted.is_(False),
            )
        ).scalar() or 0

        total_income = db.execute(
            select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
                func.date(Order.payment_time).between(
                    first_of_prev_month, last_of_prev_month
                ),
                Order.payment_status == "paid",
                Order.is_deleted.is_(False),
            )
        ).scalar() or Decimal("0")

        new_users = db.execute(
            select(func.count()).where(
                func.date(User.created_at).between(
                    first_of_prev_month, last_of_prev_month
                ),
                User.is_deleted.is_(False),
            )
        ).scalar() or 0

        report_data = {
            "month_start": first_of_prev_month.isoformat(),
            "month_end": last_of_prev_month.isoformat(),
            "order_count": order_count,
            "total_income": float(total_income),
            "new_users": new_users,
        }

        if existing:
            existing.data = json.dumps(report_data, cls=DecimalEncoder)
        else:
            report = MonthlyReport(
                report_date=first_of_prev_month,
                site_id=1,
                data=json.dumps(report_data, cls=DecimalEncoder),
            )
            db.add(report)

    return report_data
