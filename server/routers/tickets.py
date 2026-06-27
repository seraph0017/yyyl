"""
验票路由

C端：
- GET /api/v1/tickets/{id} — 票详情
- POST /api/v1/tickets/{id}/refresh-qr — 刷新 QR Token

员工端：
- GET /api/v1/staff/orders/today — 今日订单
- GET /api/v1/staff/orders/{id} — 员工端订单详情
- GET /api/v1/staff/tickets/pending — 待核销列表
- GET /api/v1/staff/tickets/logs — 核销历史
- POST /api/v1/staff/tickets/scan — 扫码验票
- POST /api/v1/staff/tickets/verify-code — 年卡验证码验证
- GET /api/v1/staff/tickets/verify-status/{session_id} — 验票状态轮询
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_staff_principal, get_current_user
from middleware.site import get_site_id
from models.user import User
from schemas.common import ResponseModel
from schemas.order import (
    TicketRefreshResponse,
    TicketResponse,
    TicketScanRequest,
    TicketScanResponse,
    StaffOrderDetailResponse,
    StaffPendingTicketResponse,
    StaffTicketLogResponse,
    StaffTodayOrderResponse,
    VerifyCodeRequest,
    VerifyStatusResponse,
)
from services import ticket_service

router = APIRouter(tags=["验票"])


# ========== C端接口 ==========

@router.get("/api/v1/tickets/{ticket_id}", summary="电子票详情")
async def get_ticket_detail(
    ticket_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取电子票详情（含二维码Token）"""
    site_id = get_site_id(request)
    ticket = await ticket_service.get_ticket_detail(
        db,
        ticket_id,
        user_id=user.id,
        site_id=site_id,
    )
    payload = await ticket_service.build_ticket_response(db, ticket)
    await db.commit()
    result = TicketResponse.model_validate(payload)
    return ResponseModel.success(data=result)


@router.post("/api/v1/tickets/{ticket_id}/refresh-qr", summary="刷新二维码Token")
async def refresh_qr_token(
    ticket_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """刷新电子票的二维码Token（30秒有效），防止截图盗用"""
    site_id = get_site_id(request)
    result = await ticket_service.refresh_qr_token(
        db,
        ticket_id,
        user.id,
        site_id=site_id,
    )
    await db.commit()
    refresh_resp = TicketRefreshResponse.model_validate(result)
    return ResponseModel.success(data=refresh_resp)


# ========== 员工端接口 ==========

@router.get("/api/v1/staff/orders/today", summary="员工端今日订单")
async def list_staff_today_orders(
    target_date: Optional[date] = Query(default=None, description="查询日期，默认今天"),
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """员工端查看今日订单与核销状态。"""
    data = await ticket_service.list_staff_today_orders(
        db,
        staff_site_id=staff.site_id,
        target_date=target_date,
    )
    items = [StaffTodayOrderResponse.model_validate(item) for item in data]
    return ResponseModel.success(data=items)


@router.get("/api/v1/staff/orders/{order_id}", summary="员工端订单详情")
async def get_staff_order_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """员工端查看订单详情、订单项与票券核销状态。"""
    data = await ticket_service.get_staff_order_detail(
        db,
        order_id=order_id,
        staff_site_id=staff.site_id,
    )
    result = StaffOrderDetailResponse.model_validate(data)
    return ResponseModel.success(data=result)


@router.get("/api/v1/staff/tickets/pending", summary="员工端待核销列表")
async def list_staff_pending_tickets(
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """员工端查看待核销票券。"""
    data = await ticket_service.list_staff_pending_tickets(
        db,
        staff_site_id=staff.site_id,
    )
    items = [StaffPendingTicketResponse.model_validate(item) for item in data]
    return ResponseModel.success(data=items)


@router.get("/api/v1/staff/tickets/logs", summary="员工端核销历史")
async def list_staff_ticket_logs(
    limit: int = Query(default=100, ge=1, le=500, description="返回数量"),
    only_me: bool = Query(default=False, description="只看当前员工"),
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """员工端查看核销历史。"""
    data = await ticket_service.list_staff_ticket_logs(
        db,
        staff_site_id=staff.site_id,
        staff_id=staff.id if only_me else None,
        staff_source=staff.source if only_me else None,
        limit=limit,
    )
    items = [StaffTicketLogResponse.model_validate(item) for item in data]
    return ResponseModel.success(data=items)


@router.post("/api/v1/staff/tickets/scan", summary="扫码验票")
async def scan_ticket(
    body: TicketScanRequest,
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """
    员工扫码验票：
    - 普通票：直接验票完成
    - 年卡票：返回验证码，需要用户在小程序上输入确认
    """
    result = await ticket_service.scan_ticket(
        db,
        body.qr_token,
        staff_id=staff.id,
        device_info=body.device_info,
        staff_site_id=staff.site_id,
        staff_source=staff.source,
    )
    scan_resp = TicketScanResponse.model_validate(result)
    return ResponseModel.success(data=scan_resp)


@router.post("/api/v1/staff/tickets/verify-code", summary="年卡验证码验证")
async def verify_code(
    body: VerifyCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    用户端输入验证码确认（年卡验票流程）：
    员工扫码后生成验证码 → 通知用户 → 用户在小程序输入验证码 → 验票完成
    """
    site_id = get_site_id(request)
    result = await ticket_service.verify_code(
        db, body.session_id, body.code, user.id, site_id=site_id,
    )
    return ResponseModel.success(data=result)


@router.get(
    "/api/v1/staff/tickets/verify-status/{session_id}",
    summary="验票状态轮询",
)
async def get_verify_status(
    session_id: str,
    staff = Depends(get_current_staff_principal),
):
    """
    员工端轮询验票状态：
    - waiting：等待用户输入验证码
    - code_sent：验证码已发送
    - verified：验票完成
    - expired：会话已过期
    """
    result = await ticket_service.get_verify_status(
        session_id,
        staff_id=staff.id,
        staff_site_id=staff.site_id,
        staff_source=staff.source,
    )
    status_resp = VerifyStatusResponse.model_validate(result)
    return ResponseModel.success(data=status_resp)
