"""
某露营地 — Celery Beat 定时任务配置

24 个定时任务，按业务分类：
- 开票/库存类 (2)
- 订单类 (2)
- 会员类 (5)
- 财务类 (2)
- 数据统计类 (5)
- 通知类 (3)
- 清理类 (4)
- CMS类 (1)
"""

from celery.schedules import crontab

beat_schedule = {
    # ===== 开票/库存类 =====
    "auto-release-tickets": {
        "task": "tasks.inventory.task_auto_release_tickets",
        "schedule": crontab(minute="*/1"),
        "options": {"queue": "inventory"},
    },
    "inventory-auto-release": {
        "task": "tasks.inventory.task_inventory_auto_release",
        "schedule": crontab(minute="*/1"),
        "options": {"queue": "inventory"},
    },

    # ===== 订单类 =====
    "cancel-expired-orders": {
        "task": "tasks.order.task_cancel_expired_orders",
        "schedule": crontab(minute="*/1"),
        "options": {"queue": "order"},
    },
    "auto-complete-orders": {
        "task": "tasks.order.task_auto_complete_orders",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "order"},
    },

    # ===== 会员类 =====
    "annual-card-expire": {
        "task": "tasks.member.task_annual_card_expire",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "member"},
    },
    "times-card-expire": {
        "task": "tasks.member.task_times_card_expire",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "member"},
    },
    "annual-card-expire-remind": {
        "task": "tasks.member.task_annual_card_expire_remind",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "notification"},
    },
    "times-card-expire-remind": {
        "task": "tasks.member.task_times_card_expire_remind",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "notification"},
    },
    "points-expire": {
        "task": "tasks.member.task_points_expire",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "member"},
    },

    # ===== 财务类 =====
    "income-confirm": {
        "task": "tasks.finance.task_income_confirm",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "finance"},
    },
    "deposit-timeout-alert": {
        "task": "tasks.finance.task_deposit_timeout_alert",
        "schedule": crontab(hour=10, minute=0),
        "options": {"queue": "notification"},
    },

    # ===== 数据统计类 =====
    "dashboard-aggregate": {
        "task": "tasks.stats.task_dashboard_aggregate",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "stats"},
    },
    "heatmap-calculate": {
        "task": "tasks.stats.task_heatmap_calculate",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "stats"},
    },
    "daily-report": {
        "task": "tasks.stats.task_daily_report",
        "schedule": crontab(hour=5, minute=0),
        "options": {"queue": "stats"},
    },
    "weekly-report": {
        "task": "tasks.stats.task_weekly_report",
        "schedule": crontab(hour=5, minute=0, day_of_week=1),
        "options": {"queue": "stats"},
    },
    "monthly-report": {
        "task": "tasks.stats.task_monthly_report",
        "schedule": crontab(hour=6, minute=0, day_of_month=1),
        "options": {"queue": "stats"},
    },

    # ===== 通知类 =====
    "trip-remind": {
        "task": "tasks.notification.task_trip_remind",
        "schedule": crontab(hour=18, minute=0),
        "options": {"queue": "notification"},
    },
    "activity-start-remind": {
        "task": "tasks.notification.task_activity_start_remind",
        "schedule": crontab(minute="*/1"),
        "options": {"queue": "notification"},
    },
    "refund-approval-timeout": {
        "task": "tasks.notification.task_refund_approval_timeout",
        "schedule": crontab(minute=0, hour="*/2"),
        "options": {"queue": "notification"},
    },

    # ===== 清理类 =====
    "cleanup-expired-tokens": {
        "task": "tasks.cleanup.task_cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "cleanup"},
    },
    "cleanup-expired-verify-codes": {
        "task": "tasks.cleanup.task_cleanup_expired_verify_codes",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "cleanup"},
    },
    "log-archive": {
        "task": "tasks.cleanup.task_log_archive",
        "schedule": crontab(hour=4, minute=0, day_of_month=1),
        "options": {"queue": "cleanup"},
    },
    "inventory-consistency-check": {
        "task": "tasks.inventory.task_inventory_consistency_check",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "inventory"},
    },

    # ===== CMS类 =====
    "cms-cleanup-versions": {
        "task": "cms.cleanup_old_versions",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨3点
        "options": {"queue": "cleanup"},
    },
}
