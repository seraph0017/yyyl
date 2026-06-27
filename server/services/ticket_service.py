"""
验票服务

- get_ticket_detail：获取电子票详情
- refresh_qr_token：刷新二维码Token
- scan_ticket：扫码验票
- verify_code：年卡验证码验证
- get_verify_status：验票状态轮询
"""

from __future__ import annotations

import logging
import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory
from models.order import Order, OrderItem, Ticket, TicketVerifyLog
from models.product import Product
from models.user import User
from redis_client import get_redis
from utils.helpers import generate_qr_token, generate_verification_code

logger = logging.getLogger(__name__)

VERIFIABLE_ORDER_STATUSES = {"paid", "verified", "completed"}
VERIFIABLE_REFUND_STATUSES = {"none", "rejected"}
STAFF_SOURCES = {"user", "admin"}


def _hash_qr_token(qr_token: str) -> str:
    return hashlib.sha256(qr_token.encode("utf-8")).hexdigest()


def _mask_phone(phone: Optional[str]) -> Optional[str]:
    """手机号脱敏：138****1234。"""
    if phone and len(phone) >= 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone


def _normalize_staff_source(staff_source: Optional[str]) -> str:
    return staff_source if staff_source in STAFF_SOURCES else "user"


def _is_ticket_verifiable(ticket: Optional[Ticket]) -> bool:
    return bool(ticket and ticket.verify_status == "pending")


def _is_order_verifiable(order: Any, *, site_id: Optional[int] = None) -> bool:
    if order is None or getattr(order, "is_deleted", False):
        return False
    if site_id is not None and getattr(order, "site_id", site_id) != site_id:
        return False
    refund_status = getattr(order, "refund_status", "none") or "none"
    return (
        getattr(order, "payment_status", None) == "paid"
        and getattr(order, "status", None) in VERIFIABLE_ORDER_STATUSES
        and refund_status in VERIFIABLE_REFUND_STATUSES
    )


def _ticket_payload(ticket: Ticket) -> Dict[str, Any]:
    return {
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "ticket_type": ticket.ticket_type,
        "verify_status": ticket.verify_status,
        "verify_date": ticket.verify_date,
        "verified_at": ticket.verified_at,
        "verified_by": ticket.verified_by,
        "current_verify_count": ticket.current_verify_count,
        "total_verify_count": ticket.total_verify_count,
        "can_verify": _is_ticket_verifiable(ticket),
    }


async def _create_ticket_verify_log(
    db: AsyncSession,
    *,
    ticket: Optional[Ticket],
    staff_id: int,
    verify_result: str,
    staff_source: str = "user",
    failure_reason: Optional[str] = None,
    qr_token: Optional[str] = None,
    device_info: Optional[str] = None,
    site_id: Optional[int] = None,
    commit_immediately: bool = False,
) -> None:
    """记录核销尝试，成功/失败/重复都留痕。"""
    log_data = {
        "site_id": site_id or getattr(ticket, "site_id", None) or 1,
        "ticket_id": getattr(ticket, "id", None),
        "order_id": getattr(ticket, "order_id", None),
        "order_item_id": getattr(ticket, "order_item_id", None),
        "staff_id": staff_id,
        "staff_source": _normalize_staff_source(staff_source),
        "verify_result": verify_result,
        "failure_reason": failure_reason,
        "device_info": device_info,
        "qr_token_hash": _hash_qr_token(qr_token) if qr_token else None,
    }
    if commit_immediately:
        # 异常路径的业务会话随后会 rollback；独立审计事务不能引用当前事务
        # 可能持有 FOR UPDATE 锁的票券行，否则 PostgreSQL 外键检查可能自等待。
        log_data["ticket_id"] = None
        log_data["order_id"] = None
        log_data["order_item_id"] = None
        async with async_session_factory() as audit_session:
            audit_session.add(TicketVerifyLog(**log_data))
            await audit_session.commit()
        return

    db.add(TicketVerifyLog(**log_data))


async def get_ticket_detail(
    db: AsyncSession,
    ticket_id: int,
    user_id: Optional[int] = None,
    site_id: Optional[int] = None,
) -> Ticket:
    """获取电子票详情

    Args:
        db: 数据库会话
        ticket_id: 票ID
        user_id: 用户ID（可选，用于权限校验）

    Returns:
        Ticket 实例
    """
    query = select(Ticket).where(
        Ticket.id == ticket_id,
        Ticket.is_deleted.is_(False),
    )
    if user_id:
        query = query.where(Ticket.user_id == user_id)
    if site_id is not None:
        query = query.where(Ticket.site_id == site_id)

    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "电子票不存在"},
        )

    return ticket


async def build_ticket_response(
    db: AsyncSession,
    ticket: Ticket,
    *,
    refresh_token: bool = True,
) -> Dict[str, Any]:
    """构造 C 端票券响应，明文二维码 token 只在响应中短暂出现。"""
    qr_token = None
    now = datetime.now(timezone.utc)
    if refresh_token and ticket.verify_status == "pending":
        qr_token = generate_qr_token()
        ticket.qr_token_hash = _hash_qr_token(qr_token)
        ticket.qr_token_expires_at = now + timedelta(seconds=30)
        await db.flush()

    return {
        "id": ticket.id,
        "order_id": ticket.order_id,
        "order_item_id": ticket.order_item_id,
        "user_id": ticket.user_id,
        "ticket_no": ticket.ticket_no,
        "ticket_type": ticket.ticket_type,
        "qr_token": qr_token or "",
        "qrcode_token": qr_token or "",
        "qr_token_expires_at": ticket.qr_token_expires_at,
        "verify_date": ticket.verify_date,
        "date": ticket.verify_date,
        "verified_at": ticket.verified_at,
        "verified_by": ticket.verified_by,
        "verify_status": ticket.verify_status,
        "status": {
            "pending": "unused",
            "verified": "used",
            "expired": "expired",
        }.get(ticket.verify_status, ticket.verify_status),
        "total_verify_count": ticket.total_verify_count,
        "current_verify_count": ticket.current_verify_count,
        "created_at": ticket.created_at,
        "product_name": getattr(ticket, "product_name", None),
        "product_image": getattr(ticket, "product_image", None),
    }


async def refresh_qr_token(
    db: AsyncSession,
    ticket_id: int,
    user_id: int,
    site_id: Optional[int] = None,
) -> Dict[str, Any]:
    """刷新二维码Token（30秒有效）

    Args:
        db: 数据库会话
        ticket_id: 票ID
        user_id: 用户ID

    Returns:
        新的qr_token和过期时间
    """
    ticket = await get_ticket_detail(db, ticket_id, user_id, site_id=site_id)

    if ticket.verify_status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票已验证"},
        )
    if ticket.verify_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票不可刷新二维码"},
        )

    new_token = generate_qr_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)

    ticket.qr_token_hash = _hash_qr_token(new_token)
    ticket.qr_token_expires_at = expires_at
    await db.flush()

    return {
        "ticket_id": ticket.id,
        "qr_token": new_token,
        "qrcode_token": new_token,
        "qr_token_expires_at": expires_at,
    }


async def scan_ticket(
    db: AsyncSession,
    qr_token: str,
    staff_id: int,
    device_info: Optional[str] = None,
    staff_site_id: Optional[int] = None,
    staff_source: str = "user",
) -> Dict[str, Any]:
    """员工扫码验票

    Args:
        db: 数据库会话
        qr_token: 扫到的二维码Token
        staff_id: 员工ID

    Returns:
        验票结果（含是否需要年卡验证码）
    """
    qr_token_hash = _hash_qr_token(qr_token)
    staff_source = _normalize_staff_source(staff_source)

    # 查找对应的电子票
    query = select(Ticket).where(
        Ticket.qr_token_hash == qr_token_hash,
        Ticket.is_deleted.is_(False),
    )
    if staff_site_id is not None:
        query = query.where(Ticket.site_id == staff_site_id)

    result = await db.execute(
        query.with_for_update()
    )
    ticket = result.scalar_one_or_none()

    if ticket is None:
        await _create_ticket_verify_log(
            db,
            ticket=None,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=staff_source,
            failure_reason="二维码无效",
            qr_token=qr_token,
            device_info=device_info,
            site_id=staff_site_id,
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40917, "message": "二维码无效"},
        )

    # 检查是否过期
    if datetime.now(timezone.utc) > ticket.qr_token_expires_at:
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=staff_source,
            failure_reason="二维码已过期",
            qr_token=qr_token,
            device_info=device_info,
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40918, "message": "二维码已过期，请让用户刷新"},
        )

    if ticket.verify_status == "verified":
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="duplicate",
            staff_source=staff_source,
            failure_reason="电子票已验证",
            qr_token=qr_token,
            device_info=device_info,
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票已验证"},
        )

    if ticket.verify_status != "pending":
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=staff_source,
            failure_reason="电子票不可核销",
            qr_token=qr_token,
            device_info=device_info,
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票不可核销"},
        )

    # 检查日期
    if ticket.verify_date and ticket.verify_date != date.today():
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=staff_source,
            failure_reason=f"电子票使用日期为{ticket.verify_date}，不是今天",
            qr_token=qr_token,
            device_info=device_info,
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": f"电子票使用日期为{ticket.verify_date}，不是今天"},
        )

    # 判断是否是年卡票，需要验证码流程
    needs_verification_code = False
    order_query = select(Order).where(Order.id == ticket.order_id)
    if staff_site_id is not None:
        order_query = order_query.where(Order.site_id == staff_site_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()
    if not _is_order_verifiable(order, site_id=staff_site_id):
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=staff_source,
            failure_reason="订单不可核销",
            qr_token=qr_token,
            device_info=device_info,
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40919, "message": "订单不可核销"},
        )
    if order and getattr(order, "payment_method", None) == "annual_card_free":
        needs_verification_code = True

    redis = get_redis()
    import uuid
    session_id = uuid.uuid4().hex

    verification_code = None

    if needs_verification_code:
        # 年卡验票流程：生成验证码，存Redis
        verification_code = generate_verification_code()
        await redis.set(
            f"verify_session:{session_id}",
            f"{ticket.id}:{verification_code}:{staff_id}:{ticket.site_id}:{staff_source}",
            ex=300,  # 5分钟过期
        )
        await redis.set(
            f"verify_status:{session_id}",
            "code_sent",
            ex=300,
        )
    else:
        # 普通票：直接验票
        ticket.verify_status = "verified"
        ticket.verified_at = datetime.now(timezone.utc)
        ticket.verified_by = staff_id
        ticket.current_verify_count += 1
        await db.flush()

        await redis.set(
            f"verify_session_owner:{session_id}",
            f"{ticket.id}:{staff_id}:{ticket.site_id}:{staff_source}",
            ex=60,
        )
        await redis.set(
            f"verify_status:{session_id}",
            "verified",
            ex=60,
        )
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="success",
            staff_source=staff_source,
            qr_token=qr_token,
            device_info=device_info,
        )
        await db.flush()

    # 关联查询产品名称
    product_name = None
    if ticket.order_item_id:
        oi_result = await db.execute(
            select(OrderItem).where(
                OrderItem.id == ticket.order_item_id,
                OrderItem.order_id == ticket.order_id,
                OrderItem.is_deleted.is_(False),
            )
        )
        order_item = oi_result.scalar_one_or_none()
        if order_item:
            prod_result = await db.execute(
                select(Product).where(
                    Product.id == order_item.product_id,
                    Product.site_id == ticket.site_id,
                    Product.is_deleted.is_(False),
                )
            )
            prod = prod_result.scalar_one_or_none()
            if prod:
                product_name = prod.name

    return {
        "session_id": session_id,
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "ticket_type": ticket.ticket_type,
        "product_name": product_name,
        "verify_date": ticket.verify_date,
        "needs_verification_code": needs_verification_code,
        "verification_code": verification_code,
    }


async def list_staff_today_orders(
    db: AsyncSession,
    *,
    staff_site_id: int,
    target_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """员工端今日订单列表，按订单项日期或创建日期筛选。"""
    target_date = target_date or date.today()
    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(
        select(Order, OrderItem, Ticket, Product, User)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(
            Product,
            and_(
                Product.id == OrderItem.product_id,
                Product.site_id == staff_site_id,
                Product.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .join(
            Ticket,
            and_(Ticket.order_item_id == OrderItem.id, Ticket.site_id == staff_site_id),
            isouter=True,
        )
        .join(User, User.id == Order.user_id, isouter=True)
        .where(
            Order.site_id == staff_site_id,
            Order.is_deleted.is_(False),
            OrderItem.is_deleted.is_(False),
            Order.payment_status == "paid",
            Order.status.in_(VERIFIABLE_ORDER_STATUSES),
            Order.refund_status.in_(VERIFIABLE_REFUND_STATUSES),
            or_(
                OrderItem.date == target_date,
                and_(
                    OrderItem.date.is_(None),
                    Order.created_at >= day_start,
                    Order.created_at < day_end,
                ),
            ),
        )
        .order_by(Order.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "order_id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "payment_status": order.payment_status,
            "payment_time": order.payment_time,
            "actual_amount": order.actual_amount,
            "user_id": order.user_id,
            "user_nickname": user.nickname if user else None,
            "user_phone_masked": _mask_phone(user.phone if user else None),
            "order_item_id": item.id,
            "product_id": item.product_id,
            "product_name": product.name if product else None,
            "quantity": item.quantity,
            "date": item.date,
            "time_slot": item.time_slot,
            "verify_status": ticket.verify_status if ticket else "none",
            "ticket_id": ticket.id if ticket else None,
            "ticket_no": ticket.ticket_no if ticket else None,
            "can_verify": _is_ticket_verifiable(ticket),
            "remark": order.remark,
        }
        for order, item, ticket, product, user in rows
    ]


async def list_staff_pending_tickets(
    db: AsyncSession,
    *,
    staff_site_id: int,
) -> List[Dict[str, Any]]:
    """员工端待核销票券列表。"""
    result = await db.execute(
        select(Ticket, Order, OrderItem, Product, User)
        .join(Order, Order.id == Ticket.order_id)
        .join(OrderItem, OrderItem.id == Ticket.order_item_id, isouter=True)
        .join(
            Product,
            and_(
                Product.id == OrderItem.product_id,
                Product.site_id == staff_site_id,
                Product.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .join(User, User.id == Order.user_id, isouter=True)
        .where(
            Ticket.site_id == staff_site_id,
            Order.site_id == staff_site_id,
            Ticket.verify_status == "pending",
            Ticket.is_deleted.is_(False),
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
            Order.status.in_(VERIFIABLE_ORDER_STATUSES),
            Order.refund_status.in_(VERIFIABLE_REFUND_STATUSES),
        )
        .order_by(Ticket.verify_date.asc().nullslast(), Ticket.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "ticket_id": ticket.id,
            "ticket_no": ticket.ticket_no,
            "ticket_type": ticket.ticket_type,
            "order_id": order.id,
            "order_no": order.order_no,
            "order_item_id": getattr(item, "id", None),
            "user_id": order.user_id,
            "user_nickname": user.nickname if user else None,
            "user_phone_masked": _mask_phone(user.phone if user else None),
            "product_name": product.name if product else None,
            "quantity": item.quantity if item else 1,
            "date": item.date if item else ticket.verify_date,
            "time_slot": item.time_slot if item else None,
            "verify_date": ticket.verify_date,
            "verify_status": ticket.verify_status,
            "current_verify_count": ticket.current_verify_count,
            "total_verify_count": ticket.total_verify_count,
            "can_verify": True,
            "actual_amount": order.actual_amount,
            "remark": order.remark,
        }
        for ticket, order, item, product, user in rows
    ]


async def list_staff_ticket_logs(
    db: AsyncSession,
    *,
    staff_site_id: int,
    staff_id: Optional[int] = None,
    staff_source: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """员工端核销历史。"""
    conditions = [
        TicketVerifyLog.site_id == staff_site_id,
        TicketVerifyLog.is_deleted.is_(False),
    ]
    if staff_id is not None:
        conditions.append(TicketVerifyLog.staff_id == staff_id)
    if staff_source is not None:
        conditions.append(TicketVerifyLog.staff_source == _normalize_staff_source(staff_source))
    result = await db.execute(
        select(TicketVerifyLog, Ticket, Order, OrderItem, Product, User)
        .join(Ticket, Ticket.id == TicketVerifyLog.ticket_id, isouter=True)
        .join(Order, Order.id == TicketVerifyLog.order_id, isouter=True)
        .join(OrderItem, OrderItem.id == TicketVerifyLog.order_item_id, isouter=True)
        .join(
            Product,
            and_(
                Product.id == OrderItem.product_id,
                Product.site_id == staff_site_id,
                Product.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .join(User, User.id == Order.user_id, isouter=True)
        .where(*conditions)
        .order_by(TicketVerifyLog.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": log.id,
            "ticket_id": log.ticket_id,
            "ticket_no": ticket.ticket_no if ticket else None,
            "order_id": log.order_id,
            "order_no": order.order_no if order else None,
            "order_item_id": log.order_item_id,
            "product_name": product.name if product else None,
            "verify_date": ticket.verify_date if ticket else None,
            "quantity": item.quantity if item else None,
            "time_slot": item.time_slot if item else None,
            "user_nickname": user.nickname if user else None,
            "user_phone_masked": _mask_phone(user.phone if user else None),
            "staff_id": log.staff_id,
            "staff_source": getattr(log, "staff_source", "user"),
            "verify_result": log.verify_result,
            "failure_reason": log.failure_reason,
            "device_info": log.device_info,
            "remark": order.remark if order else None,
            "created_at": log.created_at,
        }
        for log, ticket, order, item, product, user in rows
    ]


async def get_staff_order_detail(
    db: AsyncSession,
    *,
    order_id: int,
    staff_site_id: int,
) -> Dict[str, Any]:
    """员工端订单详情，按营地隔离并返回核销所需字段。"""
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.site_id == staff_site_id,
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
            Order.status.in_(VERIFIABLE_ORDER_STATUSES),
            Order.refund_status.in_(VERIFIABLE_REFUND_STATUSES),
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )
    if not _is_order_verifiable(order, site_id=staff_site_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )

    item_result = await db.execute(
        select(OrderItem, Product)
        .join(
            Product,
            and_(
                Product.id == OrderItem.product_id,
                Product.site_id == staff_site_id,
                Product.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .where(OrderItem.order_id == order.id, OrderItem.is_deleted.is_(False))
        .order_by(OrderItem.id.asc())
    )
    item_rows = item_result.all()

    ticket_result = await db.execute(
        select(Ticket).where(
            Ticket.order_id == order.id,
            Ticket.site_id == staff_site_id,
            Ticket.is_deleted.is_(False),
        )
    )
    tickets = list(ticket_result.all())
    ticket_by_item: Dict[Optional[int], List[Ticket]] = {}
    for row in tickets:
        ticket = row[0] if isinstance(row, tuple) else row
        ticket_by_item.setdefault(ticket.order_item_id, []).append(ticket)

    user_result = await db.execute(
        select(User).where(User.id == order.user_id, User.is_deleted.is_(False))
    )
    user = user_result.scalar_one_or_none()

    items = []
    for item, product in item_rows:
        item_tickets = ticket_by_item.get(item.id, [])
        items.append({
            "order_item_id": item.id,
            "product_id": item.product_id,
            "sku_id": item.sku_id,
            "product_name": product.name if product else None,
            "product_image": product.cover_image if product else None,
            "quantity": item.quantity,
            "date": item.date,
            "time_slot": item.time_slot,
            "unit_price": item.unit_price,
            "actual_price": item.actual_price,
            "tickets": [_ticket_payload(ticket) for ticket in item_tickets],
        })

    return {
        "order_id": order.id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "user_nickname": user.nickname if user else None,
        "user_phone_masked": _mask_phone(user.phone if user else None),
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "payment_time": order.payment_time,
        "total_amount": order.total_amount,
        "actual_amount": order.actual_amount,
        "discount_amount": order.discount_amount,
        "remark": order.remark,
        "created_at": order.created_at,
        "items": items,
    }


async def verify_code(
    db: AsyncSession,
    session_id: str,
    code: str,
    user_id: int,
    site_id: Optional[int] = None,
) -> Dict[str, Any]:
    """年卡验证码验证

    Args:
        db: 数据库会话
        session_id: 验票会话ID
        code: 6位验证码
        user_id: 用户ID

    Returns:
        验证结果
    """
    redis = get_redis()
    session_data = await redis.get(f"verify_session:{session_id}")

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40918, "message": "验票会话已过期"},
        )

    parts = session_data.split(":")
    if len(parts) not in {3, 4, 5}:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "会话数据异常"},
        )

    ticket_id, expected_code, staff_id = int(parts[0]), parts[1], int(parts[2])
    session_site_id = int(parts[3]) if len(parts) == 4 else None
    if len(parts) >= 5:
        session_site_id = int(parts[3])
    session_staff_source = _normalize_staff_source(parts[4]) if len(parts) >= 5 else "user"
    query = select(Ticket).where(
        Ticket.id == ticket_id,
        Ticket.is_deleted.is_(False),
    )
    result = await db.execute(
        query.with_for_update()
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "电子票不存在"},
        )
    if site_id is not None and ticket.site_id != site_id:
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=session_staff_source,
            failure_reason="票券不属于当前营地",
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40303, "message": "无权验证该营地票券"},
        )
    if session_site_id is not None and ticket.site_id != session_site_id:
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=session_staff_source,
            failure_reason="票券不属于当前营地",
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40303, "message": "无权验证该营地票券"},
        )

    if getattr(ticket, "user_id", None) != user_id:
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=session_staff_source,
            failure_reason="票券不属于当前用户",
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40303, "message": "无权验证该票券"},
        )

    if ticket.verify_status == "verified":
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="duplicate",
            staff_source=session_staff_source,
            failure_reason="电子票已验证",
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票已验证"},
        )

    if ticket.verify_status != "pending":
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=session_staff_source,
            failure_reason="电子票不可核销",
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票不可核销"},
        )

    if code != expected_code:
        # 错误次数计数
        attempts_key = f"verify_attempts:{session_id}"
        attempts = await redis.incr(attempts_key)
        await redis.expire(attempts_key, 300)  # 与 session 同生命周期
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=session_staff_source,
            failure_reason="验证码错误",
            commit_immediately=True,
        )

        if attempts >= 3:
            # 达到上限，删除 session 和相关数据
            await redis.delete(f"verify_session:{session_id}")
            await redis.delete(f"verify_status:{session_id}")
            await redis.delete(attempts_key)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40917, "message": "验证码错误次数过多，请重新扫码"},
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40917, "message": f"验证码错误，剩余{3 - attempts}次机会"},
        )

    order_query = select(Order).where(Order.id == ticket.order_id)
    if session_site_id is not None:
        order_query = order_query.where(Order.site_id == session_site_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()
    if not _is_order_verifiable(order, site_id=session_site_id):
        await _create_ticket_verify_log(
            db,
            ticket=ticket,
            staff_id=staff_id,
            verify_result="failed",
            staff_source=session_staff_source,
            failure_reason="订单不可核销",
            commit_immediately=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40919, "message": "订单不可核销"},
        )

    # 验证通过，更新票状态
    ticket.verify_status = "verified"
    ticket.verified_at = datetime.now(timezone.utc)
    ticket.verified_by = staff_id
    ticket.current_verify_count += 1
    await db.flush()

    await _create_ticket_verify_log(
        db,
        ticket=ticket,
        staff_id=staff_id,
        verify_result="success",
        staff_source=session_staff_source,
    )
    await db.flush()

    # 更新 Redis 状态
    await redis.set(f"verify_status:{session_id}", "verified", ex=60)
    await redis.set(
        f"verify_session_owner:{session_id}",
        f"{ticket.id}:{staff_id}:{ticket.site_id}:{session_staff_source}",
        ex=60,
    )
    await redis.delete(f"verify_session:{session_id}")

    return {
        "session_id": session_id,
        "status": "verified",
        "message": "验票成功",
    }


async def get_verify_status(
    session_id: str,
    *,
    staff_id: Optional[int] = None,
    staff_site_id: Optional[int] = None,
    staff_source: Optional[str] = None,
) -> Dict[str, Any]:
    """验票状态轮询

    Args:
        session_id: 验票会话ID

    Returns:
        当前状态
    """
    redis = get_redis()

    status_value = await redis.get(f"verify_status:{session_id}")
    if not status_value:
        return {
            "session_id": session_id,
            "status": "expired",
            "verification_code": None,
            "message": "会话已过期",
        }

    session_staff_id: Optional[int] = None
    session_site_id: Optional[int] = None
    session_staff_source: Optional[str] = None
    session_data = await redis.get(f"verify_session:{session_id}")
    owner_data = await redis.get(f"verify_session_owner:{session_id}")
    if session_data:
        parts = session_data.split(":")
        if len(parts) >= 3:
            session_staff_id = int(parts[2])
            session_site_id = int(parts[3]) if len(parts) >= 4 else None
            session_staff_source = _normalize_staff_source(parts[4]) if len(parts) >= 5 else None
    elif owner_data:
        parts = owner_data.split(":")
        if len(parts) >= 3:
            session_staff_id = int(parts[1])
            session_site_id = int(parts[2])
            session_staff_source = _normalize_staff_source(parts[3]) if len(parts) >= 4 else None

    if session_staff_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40303, "message": "验票会话归属已过期"},
        )
    if staff_id is not None and session_staff_id != staff_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40303, "message": "无权查看该验票会话"},
        )
    if staff_site_id is not None and (session_site_id is None or session_site_id != staff_site_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40303, "message": "无权查看该营地验票会话"},
        )
    if staff_source is not None and session_staff_source is not None:
        if session_staff_source != _normalize_staff_source(staff_source):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 40303, "message": "无权查看该验票会话"},
            )

    # 如果是 code_sent，获取验证码供员工端显示
    verification_code = None
    if status_value == "code_sent":
        if session_data:
            parts = session_data.split(":")
            if len(parts) >= 2:
                verification_code = parts[1]

    return {
        "session_id": session_id,
        "status": status_value,
        "verification_code": verification_code,
        "message": None,
    }
