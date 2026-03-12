"""
某露营地 — Celery 异步任务初始化

使用 Redis 作为 Broker 和 Result Backend
"""

from celery import Celery

from config import settings

# 创建 Celery 实例
celery_app = Celery(
    "yyyl",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    # 显式列出所有任务模块（避免 autodiscover 循环导入问题）
    include=[
        "tasks.inventory",
        "tasks.order",
        "tasks.member",
        "tasks.finance",
        "tasks.notification",
        "tasks.stats",
        "tasks.cleanup",
    ],
)

# 基础配置
celery_app.conf.update(
    # 序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 结果过期时间（24小时）
    result_expires=86400,

    # 任务确认（执行完毕后确认，防止 Worker 崩溃丢任务）
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # 任务重试默认配置
    task_default_retry_delay=10,
    task_max_retries=3,

    # 队列路由
    task_routes={
        "tasks.inventory.*": {"queue": "inventory"},
        "tasks.order.*": {"queue": "order"},
        "tasks.member.*": {"queue": "member"},
        "tasks.finance.*": {"queue": "finance"},
        "tasks.notification.*": {"queue": "notification"},
        "tasks.stats.*": {"queue": "stats"},
        "tasks.cleanup.*": {"queue": "cleanup"},
    },

    # 默认队列
    task_default_queue="default",
)

# 加载 Beat 定时任务配置
from celery_config import beat_schedule  # noqa: E402

celery_app.conf.beat_schedule = beat_schedule
