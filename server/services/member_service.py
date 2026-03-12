"""
会员服务

- 年卡：购买、查询、权益校验（滑动窗口+每日限额）
- 次数卡：激活、查询、使用
- 积分：查询、兑换
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.member import (
    ActivationCode,
    AnnualCard,
    AnnualCardBookingRecord,
    AnnualCardConfig,
    PointsExchangeConfig,
    PointsRecord,
    TimesCard,
    TimesCardConfig,
    TimesConsumptionRule,
)
from models.user import User

logger = logging.getLogger(__name__)


# ---- 年卡 ----

async def get_annual_card_configs(db: AsyncSession) -> List[AnnualCardConfig]:
    """获取年卡配置列表"""
    result = await db.execute(
        select(AnnualCardConfig).where(
            AnnualCardConfig.status == "active",
            AnnualCardConfig.is_deleted.is_(False),
        ).order_by(AnnualCardConfig.price.asc())
    )
    return list(result.scalars().all())


async def get_user_annual_card(
    db: AsyncSession,
    user_id: int,
) -> Optional[AnnualCard]:
    """获取用户有效年卡"""
    today = date.today()
    result = await db.execute(
        select(AnnualCard).where(
            AnnualCard.user_id == user_id,
            AnnualCard.status == "active",
            AnnualCard.start_date <= today,
            AnnualCard.end_date >= today,
            AnnualCard.is_deleted.is_(False),
        ).order_by(AnnualCard.end_date.desc())
    )
    return result.scalar_one_or_none()


async def check_annual_card_booking(
    db: AsyncSession,
    user_id: int,
    annual_card_id: int,
    booking_dates: List[date],
) -> Dict[str, Any]:
    """年卡预定权益校验（滑动窗口+每日限额）

    Args:
        db: 数据库会话
        user_id: 用户ID
        annual_card_id: 年卡ID
        booking_dates: 预定日期列表

    Returns:
        校验结果
    """
    # 查询年卡
    result = await db.execute(
        select(AnnualCard).where(
            AnnualCard.id == annual_card_id,
            AnnualCard.user_id == user_id,
            AnnualCard.is_deleted.is_(False),
        )
    )
    card = result.scalar_one_or_none()

    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "年卡不存在"},
        )

    if card.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40914, "message": "年卡已过期"},
        )

    # 获取配置
    cfg_result = await db.execute(
        select(AnnualCardConfig).where(AnnualCardConfig.id == card.config_id)
    )
    config = cfg_result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "年卡配置异常"},
        )

    # 查询预定记录（滑动窗口计算）
    window_start = min(booking_dates) - timedelta(days=config.max_consecutive_days + config.gap_days)
    records_result = await db.execute(
        select(AnnualCardBookingRecord).where(
            AnnualCardBookingRecord.annual_card_id == annual_card_id,
            AnnualCardBookingRecord.booking_date >= window_start,
            AnnualCardBookingRecord.status == "active",
            AnnualCardBookingRecord.is_deleted.is_(False),
        ).order_by(AnnualCardBookingRecord.booking_date.asc())
    )
    existing_records = list(records_result.scalars().all())
    existing_dates = {r.booking_date for r in existing_records}

    # 每日限额检查
    today = date.today()
    today_count = sum(1 for r in existing_records if r.booking_date == today)

    # 连续天数检查（滑动窗口）
    all_dates = sorted(existing_dates | set(booking_dates))
    current_consecutive = 0
    max_found = 0
    for i, d in enumerate(all_dates):
        if i == 0 or (d - all_dates[i - 1]).days == 1:
            current_consecutive += 1
        else:
            current_consecutive = 1
        max_found = max(max_found, current_consecutive)

    can_book = True
    reason = None

    if today_count >= config.daily_limit_position:
        can_book = False
        reason = "年卡每日限额已满"

    if max_found > config.max_consecutive_days:
        can_book = False
        reason = f"超过最大连续{config.max_consecutive_days}天限制"

    return {
        "can_book": can_book,
        "reason": reason,
        "daily_limit_position": config.daily_limit_position,
        "daily_limit_quantity": config.daily_limit_quantity,
        "used_today_position": today_count,
        "used_today_quantity": today_count,
        "max_consecutive_days": config.max_consecutive_days,
        "current_consecutive_days": max_found,
        "gap_days": config.gap_days,
        "next_available_date": None,
    }


# ---- 次数卡 ----

async def activate_times_card(
    db: AsyncSession,
    user_id: int,
    activation_code: str,
) -> TimesCard:
    """激活次数卡

    Args:
        db: 数据库会话
        user_id: 用户ID
        activation_code: 激活码

    Returns:
        激活的 TimesCard 实例
    """
    # 查找激活码
    result = await db.execute(
        select(ActivationCode).where(
            ActivationCode.code == activation_code,
            ActivationCode.is_deleted.is_(False),
        )
    )
    code_record = result.scalar_one_or_none()

    if code_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40911, "message": "激活码不存在或无效"},
        )

    if code_record.status == "used":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40910, "message": "激活码已使用"},
        )

    if code_record.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40911, "message": "激活码已过期"},
        )

    if code_record.expires_at and datetime.now(timezone.utc) > code_record.expires_at:
        code_record.status = "expired"
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40911, "message": "激活码已过期"},
        )

    # 获取配置
    cfg_result = await db.execute(
        select(TimesCardConfig).where(TimesCardConfig.id == code_record.config_id)
    )
    config = cfg_result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "次数卡配置异常"},
        )

    # 创建次数卡
    now = datetime.now(timezone.utc)
    start = now.date()
    end = start + timedelta(days=config.validity_days - 1)

    times_card = TimesCard(
        user_id=user_id,
        config_id=config.id,
        activation_code_id=code_record.id,
        total_times=config.total_times,
        remaining_times=config.total_times,
        start_date=start,
        end_date=end,
        activated_at=now,
        status="active",
    )
    db.add(times_card)

    # 标记激活码已使用
    code_record.status = "used"
    code_record.used_by = user_id
    code_record.used_at = now

    await db.flush()
    logger.info(f"[会员] 次数卡激活: user={user_id}, card_id={times_card.id}")
    return times_card


async def get_user_times_cards(
    db: AsyncSession,
    user_id: int,
) -> List[TimesCard]:
    """获取用户的次数卡列表"""
    result = await db.execute(
        select(TimesCard).where(
            TimesCard.user_id == user_id,
            TimesCard.is_deleted.is_(False),
        ).order_by(TimesCard.created_at.desc())
    )
    return list(result.scalars().all())


# ---- 积分 ----

async def get_points_balance(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    """获取积分余额"""
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40403, "message": "用户不存在"},
        )

    # 查询累计获取/消耗
    earn_result = await db.execute(
        select(func.coalesce(func.sum(PointsRecord.change_amount), 0)).where(
            PointsRecord.user_id == user_id,
            PointsRecord.change_type == "earn",
        )
    )
    total_earned = earn_result.scalar() or 0

    consume_result = await db.execute(
        select(func.coalesce(func.sum(func.abs(PointsRecord.change_amount)), 0)).where(
            PointsRecord.user_id == user_id,
            PointsRecord.change_type == "consume",
        )
    )
    total_consumed = consume_result.scalar() or 0

    return {
        "balance": user.points_balance,
        "total_earned": total_earned,
        "total_consumed": total_consumed,
        "expiring_soon": None,  # TODO: 计算即将过期积分
        "expiring_date": None,
    }


async def get_points_records(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[PointsRecord], int]:
    """获取积分变动记录"""
    query = select(PointsRecord).where(
        PointsRecord.user_id == user_id,
        PointsRecord.is_deleted.is_(False),
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(PointsRecord.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    records = list(result.scalars().all())

    return records, total


async def exchange_points(
    db: AsyncSession,
    user_id: int,
    exchange_config_id: int,
    quantity: int = 1,
) -> Dict[str, Any]:
    """积分兑换

    Args:
        db: 数据库会话
        user_id: 用户ID
        exchange_config_id: 兑换活动配置ID
        quantity: 兑换数量

    Returns:
        兑换结果
    """
    # 查询兑换配置
    cfg_result = await db.execute(
        select(PointsExchangeConfig).where(
            PointsExchangeConfig.id == exchange_config_id,
            PointsExchangeConfig.status == "active",
            PointsExchangeConfig.is_deleted.is_(False),
        )
    )
    config = cfg_result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "兑换活动不存在或已结束"},
        )

    now = datetime.now(timezone.utc)
    if now < config.start_at or now > config.end_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "兑换活动不在有效期内"},
        )

    # 库存检查
    remaining_stock = config.stock - config.stock_used
    if remaining_stock < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": "兑换库存不足"},
        )

    # 积分检查
    points_needed = config.points_required * quantity
    user_result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = user_result.scalar_one_or_none()

    if user is None or user.points_balance < points_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40908, "message": f"积分不足，需要{points_needed}积分"},
        )

    # 扣减积分
    user.points_balance -= points_needed

    # 记录积分变动
    record = PointsRecord(
        user_id=user_id,
        change_amount=-points_needed,
        balance_after=user.points_balance,
        change_type="consume",
        reason=f"积分兑换: {config.name}",
    )
    db.add(record)

    # 更新兑换库存
    config.stock_used += quantity

    await db.flush()
    logger.info(
        f"[会员] 积分兑换: user={user_id}, config={exchange_config_id}, points={points_needed}"
    )

    return {
        "success": True,
        "points_consumed": points_needed,
        "remaining_balance": user.points_balance,
    }
