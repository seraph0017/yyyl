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
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Ticket
from redis_client import get_redis
from utils.helpers import generate_qr_token, generate_verification_code

logger = logging.getLogger(__name__)


async def get_ticket_detail(
    db: AsyncSession,
    ticket_id: int,
    user_id: Optional[int] = None,
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

    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "电子票不存在"},
        )

    return ticket


async def refresh_qr_token(
    db: AsyncSession,
    ticket_id: int,
    user_id: int,
) -> Dict[str, Any]:
    """刷新二维码Token（30秒有效）

    Args:
        db: 数据库会话
        ticket_id: 票ID
        user_id: 用户ID

    Returns:
        新的qr_token和过期时间
    """
    ticket = await get_ticket_detail(db, ticket_id, user_id)

    if ticket.verify_status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票已验证"},
        )

    new_token = generate_qr_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)

    ticket.qr_token = new_token
    ticket.qr_token_expires_at = expires_at
    await db.flush()

    return {
        "ticket_id": ticket.id,
        "qr_token": new_token,
        "qr_token_expires_at": expires_at,
    }


async def scan_ticket(
    db: AsyncSession,
    qr_token: str,
    staff_id: int,
) -> Dict[str, Any]:
    """员工扫码验票

    Args:
        db: 数据库会话
        qr_token: 扫到的二维码Token
        staff_id: 员工ID

    Returns:
        验票结果（含是否需要年卡验证码）
    """
    # 查找对应的电子票
    result = await db.execute(
        select(Ticket).where(
            Ticket.qr_token == qr_token,
            Ticket.is_deleted.is_(False),
        )
    )
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40917, "message": "二维码无效"},
        )

    # 检查是否过期
    if datetime.now(timezone.utc) > ticket.qr_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40918, "message": "二维码已过期，请让用户刷新"},
        )

    if ticket.verify_status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "电子票已验证"},
        )

    # 检查日期
    if ticket.verify_date and ticket.verify_date != date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": f"电子票使用日期为{ticket.verify_date}，不是今天"},
        )

    redis = get_redis()
    import uuid
    session_id = uuid.uuid4().hex

    # TODO: 判断是否是年卡票，需要验证码流程
    needs_verification_code = False
    verification_code = None

    if needs_verification_code:
        # 年卡验票流程：生成验证码，存Redis
        verification_code = generate_verification_code()
        await redis.set(
            f"verify_session:{session_id}",
            f"{ticket.id}:{verification_code}:{staff_id}",
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
            f"verify_status:{session_id}",
            "verified",
            ex=60,
        )

    return {
        "session_id": session_id,
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "ticket_type": ticket.ticket_type,
        "product_name": None,  # TODO: 关联查询
        "verify_date": ticket.verify_date,
        "needs_verification_code": needs_verification_code,
        "verification_code": verification_code,
    }


async def verify_code(
    db: AsyncSession,
    session_id: str,
    code: str,
    user_id: int,
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
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50001, "message": "会话数据异常"},
        )

    ticket_id, expected_code, staff_id = int(parts[0]), parts[1], int(parts[2])

    if code != expected_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40917, "message": "验证码错误"},
        )

    # 验证通过，更新票状态
    ticket = await get_ticket_detail(db, ticket_id)
    ticket.verify_status = "verified"
    ticket.verified_at = datetime.now(timezone.utc)
    ticket.verified_by = staff_id
    ticket.current_verify_count += 1
    await db.flush()

    # 更新 Redis 状态
    await redis.set(f"verify_status:{session_id}", "verified", ex=60)
    await redis.delete(f"verify_session:{session_id}")

    return {
        "session_id": session_id,
        "status": "verified",
        "message": "验票成功",
    }


async def get_verify_status(session_id: str) -> Dict[str, Any]:
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

    # 如果是 code_sent，获取验证码供用户端显示
    verification_code = None
    if status_value == "code_sent":
        session_data = await redis.get(f"verify_session:{session_id}")
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
