"""
会员路由

- GET /annual-card — 年卡信息
- POST /annual-card/purchase — 购买年卡
- GET /annual-card/booking-check — 预定权益校验
- GET /times-cards — 次数卡列表
- POST /times-cards/activate — 激活次数卡
- GET /points — 积分信息
- POST /points/exchange — 积分兑换
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from middleware.site import get_site_id
from models.user import User
from schemas.common import ResponseModel
from schemas.member import (
    ActivationCodeActivateRequest,
    AnnualCardBookingCheck,
    AnnualCardConfigSchema,
    AnnualCardInfo,
    AnnualCardPurchaseRequest,
    PointsExchangeRequest,
    PointsInfo,
    TimesCardInfo,
)
from services import member_service

router = APIRouter(prefix="/api/v1/members", tags=["会员"])


# ========== 年卡 ==========

@router.get("/annual-card", summary="年卡信息")
async def get_annual_card(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的有效年卡信息，包含年卡配置列表"""
    site_id = get_site_id(request)
    # 用户有效年卡
    card = await member_service.get_user_annual_card(db, user.id)
    card_info = AnnualCardInfo.model_validate(card) if card else None

    # 年卡配置列表（供购买参考）—— 按 site_id 过滤
    configs = await member_service.get_annual_card_configs(db)
    config_list = [AnnualCardConfigSchema.model_validate(c) for c in configs if c.site_id == site_id]

    return ResponseModel.success(data={
        "current_card": card_info,
        "available_configs": config_list,
    })


@router.post("/annual-card/purchase", summary="购买年卡")
async def purchase_annual_card(
    body: AnnualCardPurchaseRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """购买年卡：校验身份信息→创建年卡订单"""
    # TODO: member_service.purchase_annual_card(db, user, body)
    return ResponseModel.success(data=None, message="年卡购买功能开发中")


@router.get("/annual-card/booking-check", summary="年卡预定权益校验")
async def check_annual_card_booking(
    annual_card_id: int = Query(..., description="年卡ID"),
    booking_dates: str = Query(..., description="预定日期列表，逗号分隔，格式YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """校验年卡预定权益：滑动窗口连续天数限制 + 每日限额"""
    # 解析日期字符串
    dates = [date.fromisoformat(d.strip()) for d in booking_dates.split(",")]

    result = await member_service.check_annual_card_booking(
        db, user.id, annual_card_id, dates,
    )
    check_info = AnnualCardBookingCheck.model_validate(result)
    return ResponseModel.success(data=check_info)


# ========== 次数卡 ==========

@router.get("/times-cards", summary="次数卡列表")
async def list_times_cards(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的次数卡列表"""
    cards = await member_service.get_user_times_cards(db, user.id)
    items = [TimesCardInfo.model_validate(c) for c in cards]
    return ResponseModel.success(data=items)


@router.post("/times-cards/activate", summary="激活次数卡")
async def activate_times_card(
    body: ActivationCodeActivateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """使用激活码激活次数卡"""
    card = await member_service.activate_times_card(db, user.id, body.code)
    result = TimesCardInfo.model_validate(card)
    return ResponseModel.success(data=result, message="次数卡激活成功")


# ========== 积分 ==========

@router.get("/points", summary="积分信息")
async def get_points_info(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的积分余额和累计信息"""
    result = await member_service.get_points_balance(db, user.id)
    points_info = PointsInfo.model_validate(result)
    return ResponseModel.success(data=points_info)


@router.post("/points/exchange", summary="积分兑换")
async def exchange_points(
    body: PointsExchangeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """积分兑换商品/权益"""
    result = await member_service.exchange_points(
        db, user.id, body.exchange_config_id, body.quantity,
    )
    return ResponseModel.success(data=result, message="兑换成功")
