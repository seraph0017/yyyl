"""
CMS 定时任务
- 版本快照清理：每天凌晨 3 点执行
"""

from celery_app import celery_app
from database import get_sync_session
from models.cms import CmsPage, CmsPageVersion
from sqlalchemy import select, func


@celery_app.task(name="cms.cleanup_old_versions")
def cleanup_old_versions():
    """
    清理过期版本快照。
    规则：每个页面保留最近 20 个版本 + 始终保留 current_version_id 指向的版本。
    """
    with get_sync_session() as db:
        # 查询所有活跃页面
        pages = db.execute(
            select(CmsPage).where(CmsPage.is_deleted.is_(False))
        ).scalars().all()

        for page in pages:
            # 获取该页面的所有版本（按版本号倒序）
            versions = db.execute(
                select(CmsPageVersion)
                .where(CmsPageVersion.page_id == page.id)
                .order_by(CmsPageVersion.version_number.desc())
            ).scalars().all()

            if len(versions) <= 20:
                continue

            # 保留最近 20 个 + 当前发布版本
            keep_ids = set()
            for v in versions[:20]:
                keep_ids.add(v.id)
            if page.current_version_id:
                keep_ids.add(page.current_version_id)

            # 软删除超出的版本
            for v in versions:
                if v.id not in keep_ids:
                    v.is_deleted = True

        db.commit()
