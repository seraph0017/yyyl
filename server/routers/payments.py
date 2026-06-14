"""
微信支付通知路由
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.site import get_site_id
from services import order_service, wechat_pay_service

router = APIRouter(tags=["支付"])


@router.post("/api/v1/payments/wechat/notify", summary="微信支付结果通知")
async def wechat_payment_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """微信支付结果通知。"""
    site_id = get_site_id(request)
    body = (await request.body()).decode()
    try:
        transaction = await wechat_pay_service.parse_notification_body(
            body,
            dict(request.headers),
            site_id=site_id,
        )
        await order_service.handle_wechat_payment_notification(db, transaction)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FAIL", "message": str(exc)},
        ) from exc

    return {"code": "SUCCESS", "message": "成功"}


@router.post("/api/v1/payments/wechat/refund-notify", summary="微信退款结果通知")
async def wechat_refund_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """微信退款结果通知。"""
    site_id = get_site_id(request)
    body = (await request.body()).decode()
    try:
        refund = await wechat_pay_service.parse_notification_body(
            body,
            dict(request.headers),
            site_id=site_id,
        )
        await order_service.handle_wechat_refund_notification(db, refund)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FAIL", "message": str(exc)},
        ) from exc

    return {"code": "SUCCESS", "message": "成功"}
