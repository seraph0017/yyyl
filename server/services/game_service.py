"""
小游戏服务

- CRUD for MiniGame
- generate_game_token：生成 HMAC 签名 token（用于游戏防作弊）
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.camp_map import MiniGame

logger = logging.getLogger(__name__)

# 排序字段白名单
ALLOWED_SORT_FIELDS = {"id", "name", "sort_order", "created_at"}


async def create_mini_game(
    db: AsyncSession,
    data: Dict[str, Any],
    site_id: int = 1,
) -> MiniGame:
    """创建小游戏

    Args:
        db: 数据库会话
        data: 游戏数据
        site_id: 营地ID

    Returns:
        创建的 MiniGame 实例
    """
    game = MiniGame(site_id=site_id, **data)
    db.add(game)
    await db.flush()

    logger.info(f"[游戏] 创建: id={game.id}, name={game.name}")
    return game


async def update_mini_game(
    db: AsyncSession,
    game_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> MiniGame:
    """更新小游戏

    Args:
        db: 数据库会话
        game_id: 游戏ID
        data: 更新数据
        site_id: 营地ID

    Returns:
        更新后的 MiniGame 实例
    """
    result = await db.execute(
        select(MiniGame).where(
            MiniGame.id == game_id,
            MiniGame.site_id == site_id,
            MiniGame.is_deleted.is_(False),
        )
    )
    game = result.scalar_one_or_none()

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "小游戏不存在"},
        )

    for key, value in data.items():
        if hasattr(game, key) and value is not None:
            setattr(game, key, value)

    await db.flush()
    logger.info(f"[游戏] 更新: id={game_id}")
    return game


async def delete_mini_game(
    db: AsyncSession,
    game_id: int,
    site_id: int = 1,
) -> None:
    """删除小游戏（软删除）

    Args:
        db: 数据库会话
        game_id: 游戏ID
        site_id: 营地ID
    """
    result = await db.execute(
        select(MiniGame).where(
            MiniGame.id == game_id,
            MiniGame.site_id == site_id,
            MiniGame.is_deleted.is_(False),
        )
    )
    game = result.scalar_one_or_none()

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "小游戏不存在"},
        )

    game.is_deleted = True
    await db.flush()
    logger.info(f"[游戏] 删除: id={game_id}")


async def get_mini_game(
    db: AsyncSession,
    game_id: int,
    site_id: int = 1,
) -> MiniGame:
    """获取小游戏详情

    Args:
        db: 数据库会话
        game_id: 游戏ID
        site_id: 营地ID

    Returns:
        MiniGame 实例
    """
    result = await db.execute(
        select(MiniGame).where(
            MiniGame.id == game_id,
            MiniGame.site_id == site_id,
            MiniGame.is_deleted.is_(False),
        )
    )
    game = result.scalar_one_or_none()

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "小游戏不存在"},
        )

    return game


async def list_mini_games(
    db: AsyncSession,
    site_id: int = 1,
    game_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[MiniGame], int]:
    """小游戏列表查询

    Args:
        db: 数据库会话
        site_id: 营地ID
        game_status: 状态筛选
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        (游戏列表, 总数)
    """
    query = select(MiniGame).where(
        MiniGame.site_id == site_id,
        MiniGame.is_deleted.is_(False),
    )

    if game_status:
        query = query.where(MiniGame.status == game_status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(MiniGame, sort_by)
        query = query.order_by(
            order_col.desc() if sort_order == "desc" else order_col.asc()
        )
    else:
        query = query.order_by(MiniGame.sort_order.asc(), MiniGame.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    games = list(result.scalars().all())

    return games, total


def generate_game_token(
    user_id: int,
    secret_key: str,
    expires_in: int = 3600,
) -> Dict[str, Any]:
    """生成 HMAC 签名 token（用于游戏防作弊）

    游戏客户端凭此 token 向游戏服务端验证用户身份和请求合法性。

    Args:
        user_id: 用户ID
        secret_key: 签名密钥
        expires_in: 过期时间（秒），默认1小时

    Returns:
        包含 token 和过期时间的字典
    """
    timestamp = int(time.time())
    expire_at = timestamp + expires_in

    # 构造签名原文
    message = f"{user_id}:{timestamp}:{expire_at}"

    # HMAC-SHA256 签名
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    token = f"{user_id}.{timestamp}.{expire_at}.{signature}"

    logger.debug(f"[游戏] 生成 token: user_id={user_id}, expire_at={expire_at}")

    return {
        "token": token,
        "user_id": user_id,
        "expire_at": expire_at,
        "expires_in": expires_in,
    }
