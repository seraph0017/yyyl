"""
微信支付通知路由
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.site import get_site_id
from services import order_service, refund_service, wechat_pay_service

router = APIRouter(tags=["支付"])
logger = logging.getLogger(__name__)


def _is_idempotent_payment_notify_error(exc: HTTPException) -> bool:
    """仅对晚到或状态冲突通知 ACK，避免吞掉真实内部错误。"""
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = detail.get("code")
    return exc.status_code in {400, 404} and code in {40402, 40902, 40904}


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
        try:
            await order_service.handle_wechat_payment_notification(db, transaction)
        except HTTPException as exc:
            if _is_idempotent_payment_notify_error(exc):
                return {"code": "SUCCESS", "message": "已接收"}
            logger.exception("微信支付通知处理失败: detail=%s", exc.detail)
            raise
    except HTTPException:
        raise
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
        await refund_service.handle_wechat_refund_notification(db, refund)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FAIL", "message": str(exc)},
        ) from exc

    return {"code": "SUCCESS", "message": "成功"}
