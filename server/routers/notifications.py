"""
通知路由

- GET / — 通知列表
- PUT /{id}/read — 标记已读
- PUT /read-all — 全部已读
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
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
    # TODO: notification_service.list_notifications(db, user.id, params, pagination)
    return PaginatedResponse.create(
        items=[],
        total=0,
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
    # TODO: notification_service.mark_read(db, user.id, notification_id)
    return ResponseModel.success(message="已标记为已读")


@router.put("/read-all", summary="全部已读")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记当前用户的所有通知为已读"""
    # TODO: notification_service.mark_all_read(db, user.id)
    return ResponseModel.success(message="所有通知已标记为已读")
