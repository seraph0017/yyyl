"""
清理相关定时任务

20. task_cleanup_expired_tokens — Token清理（每天3点）
21. task_cleanup_expired_verify_codes — 验证码清理（每6小时）
22. task_log_archive — 日志归档（每月1日4点）
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from celery_app import celery_app
from models.admin import OperationLog
from models.member import ActivationCode
from tasks.helpers import get_sync_db, get_sync_redis, task_monitor

logger = logging.getLogger("celery.tasks.cleanup")


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_cleanup_expired_tokens(self):
    """Token清理：清理 Redis 中残留的无TTL异常数据

    清理范围：
    - token_blacklist:* — JWT黑名单
    - verify_session:* — 验票会话
    - verify_status:* — 验票状态
    """
    r = get_sync_redis()
    cleaned = 0

    patterns = [
        "token_blacklist:*",
        "verify_session:*",
        "verify_status:*",
    ]

    for pattern in patterns:
        for key in r.scan_iter(pattern):
            ttl = r.ttl(key)
            # 清理没有TTL（-1表示无过期时间）的残留Key
            if ttl == -1:
                r.delete(key)
                cleaned += 1
                logger.debug(f"[清理] 删除无TTL Key: {key}")

    return {"cleaned": cleaned}


@celery_app.task(bind=True, max_retries=0)
@task_monitor
def task_cleanup_expired_verify_codes(self):
    """验证码清理：清理过期的激活码

    逻辑：
    - 清理 ActivationCode 中 status='unused' 且 expires_at < now() 的记录
    - 更新状态为 expired
    """
    now = datetime.now(timezone.utc)
    cleaned = 0

    with get_sync_db() as db:
        expired_codes = db.execute(
            select(ActivationCode).where(
                ActivationCode.status == "unused",
                ActivationCode.expires_at < now,
                ActivationCode.is_deleted.is_(False),
            )
        ).scalars().all()

        for code in expired_codes:
            code.status = "expired"
            cleaned += 1

    return {"cleaned": cleaned}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
@task_monitor
def task_log_archive(self):
    """日志归档：超过90天的操作日志归档后删除

    逻辑：
    - 查询超过90天的 OperationLog 记录
    - 由于暂无 OperationLogArchive 表，目前直接删除超老日志
    - 后续可接入对象存储/日志服务归档
    """
    threshold = datetime.now(timezone.utc) - timedelta(days=90)
    deleted = 0

    with get_sync_db() as db:
        # 统计要删除的数量
        old_logs = db.execute(
            select(OperationLog).where(
                OperationLog.created_at < threshold,
            )
        ).scalars().all()

        deleted = len(old_logs)

        if deleted > 0:
            db.execute(
                delete(OperationLog).where(
                    OperationLog.created_at < threshold,
                )
            )
            logger.info(f"[日志归档] 清理 {deleted} 条超过90天的操作日志")

    return {"archived": deleted}
