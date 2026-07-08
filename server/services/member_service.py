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
from sqlalchemy.exc import IntegrityError
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
from models.order import Order
from models.user import User
from schemas.member import AnnualCardPurchaseRequest
from utils.helpers import generate_order_no
from utils.security import encrypt_sensitive, hash_sensitive, mask_id_card

logger = logging.getLogger(__name__)

_ANNUAL_PENDING_ORDER_CONSTRAINT = "uq_order_annual_pending_active"
_ANNUAL_CARD_ORDER_CONSTRAINT = "uq_ac_order"


def _integrity_error_matches(exc: IntegrityError, constraint_name: str) -> bool:
    """识别 PostgreSQL/测试替身里携带的唯一约束名。"""
    candidates = [str(exc)]
    orig = getattr(exc, "orig", None)
    if orig is not None:
        candidates.append(str(orig))
        candidates.append(str(getattr(orig, "constraint_name", "") or ""))
        diag = getattr(orig, "diag", None)
        if diag is not None:
            candidates.append(str(getattr(diag, "constraint_name", "") or ""))
    return any(constraint_name in value for value in candidates)


def _to_applicable_products(raw_value: Any) -> List[int]:
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return [int(v) for v in raw_value]
    if isinstance(raw_value, dict):
        products: List[int] = []
        for key, value in raw_value.items():
            try:
                product_id = int(key)
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict) and value.get("free", True) is False:
                continue
            products.append(product_id)
        return products
    return []


def _has_member_fields(obj: Any, fields: List[str]) -> bool:
    return all(hasattr(obj, field) for field in fields)


def serialize_membership_card_config(config: Any) -> Dict[str, Any]:
    """统一会员卡配置序列化。"""
    if _has_member_fields(config, ["card_name", "price", "duration_days", "daily_limit_position", "daily_limit_quantity"]):
        return {
            "id": config.id,
            "card_kind": "annual",
            "usage_mode": "unlimited",
            "config_name": config.card_name,
            "status": config.status,
            "start_date": None,
            "end_date": None,
            "remaining_days": None,
            "total_times": None,
            "remaining_times": None,
            "daily_limit": config.daily_limit_quantity,
            "applicable_products": _to_applicable_products(config.privileges),
            "card_name": config.card_name,
            "price": config.price,
            "duration_days": config.duration_days,
            "privileges": config.privileges,
            "daily_limit_position": config.daily_limit_position,
            "daily_limit_quantity": config.daily_limit_quantity,
            "max_consecutive_days": config.max_consecutive_days,
            "gap_days": config.gap_days,
            "refund_days": getattr(config, "refund_days", None),
        }
    if _has_member_fields(config, ["card_name", "total_times", "validity_days", "applicable_products"]):
        return {
            "id": config.id,
            "card_kind": "times",
            "usage_mode": "limited_times",
            "config_name": config.card_name,
            "status": config.status,
            "start_date": None,
            "end_date": None,
            "remaining_days": None,
            "total_times": config.total_times,
            "remaining_times": config.total_times,
            "daily_limit": config.daily_limit,
            "applicable_products": list(config.applicable_products or []),
            "card_name": config.card_name,
            "total_times_old": config.total_times,
            "validity_days": config.validity_days,
        }
    data = getattr(config, "__dict__", {}).copy()
    if "privileges" in data and isinstance(data["privileges"], dict):
        data["privileges"] = {str(key): value for key, value in data["privileges"].items()}
    data.setdefault("card_kind", "annual")
    data.setdefault("usage_mode", "unlimited")
    data.setdefault("config_name", data.get("card_name"))
    data.setdefault("applicable_products", [])
    return data


def serialize_membership_card_info(card: Any, config: Any = None) -> Dict[str, Any]:
    """统一会员卡实例序列化。"""
    if _has_member_fields(card, ["order_id", "real_name", "start_date", "end_date"]):
        config_name = getattr(getattr(card, "config", None), "card_name", None)
        if not config_name and config is not None:
            config_name = getattr(config, "card_name", None)
        if not config_name:
            config_name = getattr(card, "card_name", None) or "年卡"
        days = (card.end_date - date.today()).days if card.end_date else None
        return {
            "id": card.id,
            "user_id": card.user_id,
            "config_id": card.config_id,
            "card_kind": "annual",
            "usage_mode": "unlimited",
            "config_name": config_name,
            "status": card.status,
            "start_date": card.start_date,
            "end_date": card.end_date,
            "remaining_days": days,
            "total_times": None,
            "remaining_times": None,
            "daily_limit": getattr(config, "daily_limit_quantity", None) if config is not None else None,
            "applicable_products": _to_applicable_products(getattr(config, "privileges", {})) if config is not None else [],
            "order_id": card.order_id,
            "real_name": card.real_name,
            "id_card_masked": getattr(card, "id_card_masked", None),
            "created_at": card.created_at,
        }
    if _has_member_fields(card, ["total_times", "remaining_times", "activated_at", "start_date", "end_date"]):
        config_name = getattr(getattr(card, "config", None), "card_name", None)
        if not config_name and config is not None:
            config_name = getattr(config, "card_name", None)
        if not config_name:
            config_name = getattr(card, "card_name", None) or "次数卡"
        days = (card.end_date - date.today()).days if card.end_date else None
        applicable_products = []
        daily_limit = None
        if config is not None:
            applicable_products = list(getattr(config, "applicable_products", []) or [])
            daily_limit = getattr(config, "daily_limit", None)
        return {
            "id": card.id,
            "user_id": card.user_id,
            "config_id": card.config_id,
            "card_kind": "times",
            "usage_mode": "limited_times",
            "config_name": config_name,
            "status": card.status,
            "start_date": card.start_date,
            "end_date": card.end_date,
            "remaining_days": days,
            "total_times": card.total_times,
            "remaining_times": card.remaining_times,
            "daily_limit": daily_limit,
            "applicable_products": applicable_products,
            "activated_at": card.activated_at,
            "created_at": card.created_at,
        }
    data = getattr(card, "__dict__", {}).copy()
    data.setdefault("card_kind", "annual")
    data.setdefault("usage_mode", "unlimited")
    data.setdefault("config_name", data.get("card_name"))
    data.setdefault("applicable_products", [])
    return data


async def get_membership_card_configs(db: AsyncSession, *, site_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """获取统一会员卡配置列表。"""
    configs: List[Dict[str, Any]] = []
    annual_configs = await get_annual_card_configs(db)
    for config in annual_configs:
        if site_id is not None and getattr(config, "site_id", None) != site_id:
            continue
        configs.append(serialize_membership_card_config(config))

    result = await db.execute(
        select(TimesCardConfig).where(
            TimesCardConfig.status == "active",
            TimesCardConfig.is_deleted.is_(False),
        ).order_by(TimesCardConfig.id.asc())
    )
    for config in result.scalars().all():
        if site_id is not None and getattr(config, "site_id", None) != site_id:
            continue
        configs.append(serialize_membership_card_config(config))
    return configs


async def get_user_membership_cards(
    db: AsyncSession,
    user_id: int,
    *,
    site_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """获取用户统一会员卡列表。"""
    cards: List[Dict[str, Any]] = []
    annual_card = await get_user_annual_card(db, user_id, site_id=site_id)
    if annual_card:
        cfg_result = await db.execute(
            select(AnnualCardConfig).where(AnnualCardConfig.id == annual_card.config_id)
        )
        annual_config = cfg_result.scalar_one_or_none()
        cards.append(serialize_membership_card_info(annual_card, annual_config))

    times_cards = await get_user_times_cards(db, user_id, site_id=site_id)
    if times_cards:
        config_ids = [card.config_id for card in times_cards]
        cfg_result = await db.execute(
            select(TimesCardConfig).where(TimesCardConfig.id.in_(config_ids))
        )
        config_map = {config.id: config for config in cfg_result.scalars().all()}
        for card in times_cards:
            cards.append(serialize_membership_card_info(card, config_map.get(card.config_id)))

    return cards


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
    *,
    site_id: Optional[int] = None,
) -> Optional[AnnualCard]:
    """获取用户有效年卡"""
    today = date.today()
    conditions = [
        AnnualCard.user_id == user_id,
        AnnualCard.status == "active",
        AnnualCard.start_date <= today,
        AnnualCard.end_date >= today,
        AnnualCard.is_deleted.is_(False),
    ]
    if site_id is not None:
        conditions.append(AnnualCard.site_id == site_id)
    result = await db.execute(
        select(AnnualCard).where(*conditions).order_by(AnnualCard.end_date.desc())
    )
    if not hasattr(result, "scalars"):
        return result.scalar_one_or_none()
    scalars = result.scalars()
    if hasattr(scalars, "first"):
        return scalars.first()
    rows = list(scalars.all())
    return rows[0] if rows else None


async def check_annual_card_booking(
    db: AsyncSession,
    user_id: int,
    annual_card_id: int,
    booking_dates: List[date],
    *,
    site_id: Optional[int] = None,
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
    card_conditions = [
        AnnualCard.id == annual_card_id,
        AnnualCard.user_id == user_id,
        AnnualCard.is_deleted.is_(False),
    ]
    if site_id is not None:
        card_conditions.append(AnnualCard.site_id == site_id)
    result = await db.execute(
        select(AnnualCard).where(*card_conditions)
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
    config_conditions = [
        AnnualCardConfig.id == card.config_id,
        AnnualCardConfig.is_deleted.is_(False),
    ]
    if site_id is not None:
        config_conditions.append(AnnualCardConfig.site_id == card.site_id)
    cfg_result = await db.execute(
        select(AnnualCardConfig).where(*config_conditions)
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


async def purchase_annual_card(
    db: AsyncSession,
    user: User,
    body: AnnualCardPurchaseRequest,
    *,
    site_id: int,
) -> Order:
    """创建年卡购买订单，支付成功后再激活年卡实例。"""
    result = await db.execute(
        select(AnnualCardConfig).where(
            AnnualCardConfig.id == body.config_id,
            AnnualCardConfig.site_id == site_id,
            AnnualCardConfig.status == "active",
            AnnualCardConfig.is_deleted.is_(False),
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "年卡配置不存在或已下架"},
        )

    user_site_id = getattr(user, "site_id", None)
    if user_site_id is not None and int(user_site_id) != int(site_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "年卡配置不存在或已下架"},
        )

    user_lock_result = await db.execute(
        select(User).where(
            User.id == user.id,
            User.site_id == site_id,
            User.is_deleted.is_(False),
        ).with_for_update()
    )
    if user_lock_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "年卡配置不存在或已下架"},
        )

    active_card = await get_user_annual_card(db, user.id, site_id=site_id)
    if active_card is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40920, "message": "已存在有效年卡，无需重复购买"},
        )

    now = datetime.now(timezone.utc)
    pending_result = await db.execute(
        select(Order).where(
            Order.user_id == user.id,
            Order.site_id == site_id,
            Order.order_type == "annual_card",
            Order.status == "pending_payment",
            Order.payment_status == "unpaid",
            Order.is_deleted.is_(False),
        ).with_for_update()
    )
    pending_orders = list(pending_result.scalars().all())
    cleared_expired_order = False
    for pending_order in pending_orders:
        expire_at = getattr(pending_order, "expire_at", None)
        if expire_at and expire_at <= now:
            pending_order.status = "cancelled"
            pending_order.remark = "系统自动取消：年卡订单支付超时"
            cleared_expired_order = True
            continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40920, "message": "已存在待支付年卡订单，请先完成支付或等待订单过期"},
        )
    if cleared_expired_order:
        await db.flush()

    id_card = body.id_card.strip().upper()
    encrypted_id_card = encrypt_sensitive(id_card)
    id_card_hash = hash_sensitive(id_card)
    order = Order(
        order_no=generate_order_no(),
        user_id=user.id,
        order_type="annual_card",
        status="pending_payment",
        total_amount=config.price,
        discount_amount=Decimal("0.00"),
        actual_amount=config.price,
        deposit_amount=Decimal("0.00"),
        discount_type="none",
        discount_detail=None,
        biz_data={
            "membership_card": {
                "card_kind": "annual",
                "usage_mode": "unlimited",
                "config_id": config.id,
                "config_name": config.card_name,
                "duration_days": config.duration_days,
                "refund_days": config.refund_days,
                "real_name": body.real_name.strip(),
                "id_card_encrypted": encrypted_id_card,
                "id_card_hash": id_card_hash,
                "id_card_masked": mask_id_card(id_card),
            }
        },
        payment_method=body.payment_method,
        payment_status="unpaid",
        site_id=site_id,
        remark=f"购买会员卡：{config.card_name}",
        expire_at=now + timedelta(minutes=30),
    )
    db.add(order)
    try:
        await db.flush()
    except IntegrityError as exc:
        if _integrity_error_matches(exc, _ANNUAL_PENDING_ORDER_CONSTRAINT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40920, "message": "已存在待支付年卡订单，请先完成支付或等待订单过期"},
            ) from exc
        raise
    logger.info("[会员] 年卡购买订单创建: user=%s, config=%s, order=%s", user.id, config.id, order.id)
    return order


async def activate_annual_card_for_paid_order(
    db: AsyncSession,
    order: Order,
) -> Optional[AnnualCard]:
    """年卡订单支付成功后激活 AnnualCard，按 order_id 幂等。"""
    if getattr(order, "order_type", None) != "annual_card":
        return None

    user_lock_result = await db.execute(
        select(User).where(
            User.id == order.user_id,
            User.site_id == order.site_id,
            User.is_deleted.is_(False),
        ).with_for_update()
    )
    if user_lock_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40403, "message": "用户不存在"},
        )

    existing_result = await db.execute(
        select(AnnualCard).where(
            AnnualCard.order_id == order.id,
            AnnualCard.site_id == order.site_id,
            AnnualCard.is_deleted.is_(False),
        ).with_for_update()
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing

    today = date.today()
    active_result = await db.execute(
        select(AnnualCard).where(
            AnnualCard.user_id == order.user_id,
            AnnualCard.site_id == order.site_id,
            AnnualCard.status == "active",
            AnnualCard.start_date <= today,
            AnnualCard.end_date >= today,
            AnnualCard.order_id != order.id,
            AnnualCard.is_deleted.is_(False),
        ).with_for_update()
    )
    active_card = active_result.scalar_one_or_none()
    if active_card is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40920, "message": "已存在有效年卡，不能重复激活"},
        )

    membership_data = (getattr(order, "biz_data", None) or {}).get("membership_card") or {}
    config_id = membership_data.get("config_id")
    if not config_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "年卡订单缺少配置快照"},
        )

    cfg_result = await db.execute(
        select(AnnualCardConfig).where(
            AnnualCardConfig.id == int(config_id),
            AnnualCardConfig.site_id == order.site_id,
            AnnualCardConfig.is_deleted.is_(False),
        )
    )
    config = cfg_result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "年卡配置异常"},
        )

    real_name = str(membership_data.get("real_name") or "").strip()
    id_card_encrypted = str(membership_data.get("id_card_encrypted") or "").strip()
    id_card_hash = str(membership_data.get("id_card_hash") or "").strip()
    if not real_name or not id_card_encrypted or not id_card_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "年卡订单实名快照不完整"},
        )

    start = date.today()
    end = start + timedelta(days=config.duration_days - 1)
    card = AnnualCard(
        user_id=order.user_id,
        config_id=config.id,
        order_id=order.id,
        start_date=start,
        end_date=end,
        id_card_encrypted=id_card_encrypted,
        id_card_hash=id_card_hash,
        real_name=real_name,
        status="active",
        site_id=order.site_id,
    )
    try:
        async with db.begin_nested():
            db.add(card)
            await db.flush()
    except IntegrityError as exc:
        if _integrity_error_matches(exc, _ANNUAL_CARD_ORDER_CONSTRAINT):
            concurrent_result = await db.execute(
                select(AnnualCard).where(
                    AnnualCard.order_id == order.id,
                    AnnualCard.site_id == order.site_id,
                    AnnualCard.is_deleted.is_(False),
                ).with_for_update()
            )
            concurrent_card = concurrent_result.scalar_one_or_none()
            if concurrent_card is not None:
                return concurrent_card
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 40920, "message": "年卡订单已完成激活，请刷新后查看"},
            ) from exc
        raise
    logger.info("[会员] 年卡支付后激活: user=%s, order=%s, card=%s", order.user_id, order.id, card.id)
    return card


# ---- 次数卡 ----

async def activate_times_card(
    db: AsyncSession,
    user_id: int,
    activation_code: str,
    *,
    site_id: Optional[int] = None,
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
    code_conditions = [
        ActivationCode.code == activation_code,
        ActivationCode.is_deleted.is_(False),
    ]
    if site_id is not None:
        code_conditions.append(ActivationCode.site_id == site_id)
    result = await db.execute(select(ActivationCode).where(*code_conditions).with_for_update())
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
    config_conditions = [
        TimesCardConfig.id == code_record.config_id,
        TimesCardConfig.status == "active",
        TimesCardConfig.is_deleted.is_(False),
    ]
    if site_id is not None:
        config_conditions.append(TimesCardConfig.site_id == site_id)
    cfg_result = await db.execute(select(TimesCardConfig).where(*config_conditions).with_for_update())
    config = cfg_result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "次数卡配置异常"},
        )
    if int(getattr(code_record, "site_id", getattr(config, "site_id", site_id or 1))) != int(config.site_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "次数卡激活码营地异常"},
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
        site_id=config.site_id,
    )
    db.add(times_card)

    # 标记激活码已使用
    code_record.status = "used"
    code_record.used_by = user_id
    code_record.used_at = now

    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(times_card)
    logger.info(f"[会员] 次数卡激活: user={user_id}, card_id={times_card.id}")
    return times_card


async def get_user_times_cards(
    db: AsyncSession,
    user_id: int,
    *,
    site_id: Optional[int] = None,
) -> List[TimesCard]:
    """获取用户的次数卡列表"""
    conditions = [
        TimesCard.user_id == user_id,
        TimesCard.is_deleted.is_(False),
    ]
    if site_id is not None:
        conditions.append(TimesCard.site_id == site_id)
    result = await db.execute(
        select(TimesCard).where(*conditions).order_by(TimesCard.created_at.desc())
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

    # 计算即将过期积分（积分12个月过期，查未来30天内将过期的）
    expiring_cutoff = datetime.now(timezone.utc) - timedelta(days=335)  # 约11个月前获取的
    expiring_result = await db.execute(
        select(func.coalesce(func.sum(PointsRecord.change_amount), 0)).where(
            PointsRecord.user_id == user_id,
            PointsRecord.change_type == "earn",
            PointsRecord.created_at <= expiring_cutoff,
            PointsRecord.created_at >= expiring_cutoff - timedelta(days=30),
        )
    )
    expiring_soon = expiring_result.scalar() or 0
    expiring_date = (
        (datetime.now(timezone.utc) + timedelta(days=30)).date()
        if expiring_soon > 0
        else None
    )

    return {
        "balance": user.points_balance,
        "total_earned": total_earned,
        "total_consumed": total_consumed,
        "expiring_soon": expiring_soon if expiring_soon > 0 else None,
        "expiring_date": expiring_date,
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
