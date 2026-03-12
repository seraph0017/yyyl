"""
验票路由

C端：
- GET /api/v1/tickets/{id} — 票详情
- POST /api/v1/tickets/{id}/refresh-qr — 刷新 QR Token

员工端：
- POST /api/v1/staff/tickets/scan — 扫码验票
- POST /api/v1/staff/tickets/verify-code — 年卡验证码验证
- GET /api/v1/staff/tickets/verify-status/{session_id} — 验票状态轮询
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin, get_current_user
from models.admin import AdminUser
from models.user import User
from schemas.common import ResponseModel
from schemas.order import (
    TicketRefreshResponse,
    TicketResponse,
    TicketScanRequest,
    TicketScanResponse,
    VerifyCodeRequest,
    VerifyStatusResponse,
)
from services import ticket_service

router = APIRouter(tags=["验票"])


# ========== C端接口 ==========

@router.get("/api/v1/tickets/{ticket_id}", summary="电子票详情")
async def get_ticket_detail(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取电子票详情（含二维码Token）"""
    ticket = await ticket_service.get_ticket_detail(db, ticket_id, user_id=user.id)
    result = TicketResponse.model_validate(ticket)
    return ResponseModel.success(data=result)


@router.post("/api/v1/tickets/{ticket_id}/refresh-qr", summary="刷新二维码Token")
async def refresh_qr_token(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """刷新电子票的二维码Token（30秒有效），防止截图盗用"""
    result = await ticket_service.refresh_qr_token(db, ticket_id, user.id)
    refresh_resp = TicketRefreshResponse.model_validate(result)
    return ResponseModel.success(data=refresh_resp)


# ========== 员工端接口 ==========

@router.post("/api/v1/staff/tickets/scan", summary="扫码验票")
async def scan_ticket(
    body: TicketScanRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    员工扫码验票：
    - 普通票：直接验票完成
    - 年卡票：返回验证码，需要用户在小程序上输入确认
    """
    result = await ticket_service.scan_ticket(db, body.qr_token, staff_id=admin.id)
    scan_resp = TicketScanResponse.model_validate(result)
    return ResponseModel.success(data=scan_resp)


@router.post("/api/v1/staff/tickets/verify-code", summary="年卡验证码验证")
async def verify_code(
    body: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    用户端输入验证码确认（年卡验票流程）：
    员工扫码后生成验证码 → 通知用户 → 用户在小程序输入验证码 → 验票完成
    """
    result = await ticket_service.verify_code(
        db, body.session_id, body.code, user.id,
    )
    return ResponseModel.success(data=result)


@router.get(
    "/api/v1/staff/tickets/verify-status/{session_id}",
    summary="验票状态轮询",
)
async def get_verify_status(
    session_id: str,
    admin: AdminUser = Depends(get_current_admin),
):
    """
    员工端轮询验票状态：
    - waiting：等待用户输入验证码
    - code_sent：验证码已发送
    - verified：验票完成
    - expired：会话已过期
    """
    result = await ticket_service.get_verify_status(session_id)
    status_resp = VerifyStatusResponse.model_validate(result)
    return ResponseModel.success(data=status_resp)
