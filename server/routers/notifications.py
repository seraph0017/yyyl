"""
通知路由

- GET / — 通知列表
- PUT /{id}/read — 标记已读
- PUT /read-all — 全部已读
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.notification import Notification
from models.user import User
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.notification import NotificationListParams, NotificationResponse

router = APIRouter(prefix="/api/v1/notifications", tags=["通知"])


@router.get("/", summary="通知列表")
async def list_notifications(
    params: NotificationListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的通知列表，支持类型/已读状态筛选"""
    # 基础查询条件
    base_where = [
        Notification.user_id == user.id,
        Notification.is_deleted.is_(False),
    ]

    # 可选筛选
    if params.type is not None:
        base_where.append(Notification.type == params.type)
    if params.is_read is not None:
        base_where.append(Notification.is_read.is_(params.is_read))
    if params.channel is not None:
        base_where.append(Notification.channel == params.channel)

    # 查询总数
    count_stmt = select(func.count(Notification.id)).where(*base_where)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 查询数据（按创建时间降序）
    query = (
        select(Notification)
        .where(*base_where)
        .order_by(Notification.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    items = [
        NotificationResponse.model_validate(n) for n in notifications
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.put("/{notification_id}/read", summary="标记已读")
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记单条通知为已读"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.is_deleted.is_(False),
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "通知不存在"},
        )

    notification.is_read = True
    await db.commit()
    return ResponseModel.success(message="已标记为已读")


@router.put("/read-all", summary="全部已读")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记当前用户的所有通知为已读"""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
            Notification.is_deleted.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return ResponseModel.success(message="所有通知已标记为已读")
