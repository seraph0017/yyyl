"""
认证服务

- wx_login：微信小程序登录（code→session_key→创建/查找用户→生成token）
- admin_login：管理后台登录（用户名+密码验证）
- refresh_tokens：刷新 access_token
- get_user_info：获取当前用户信息
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.admin import AdminUser
from models.user import User
from utils.security import (
    create_access_token,
    create_refresh_token,
    get_token_expire_seconds,
    verify_password,
    verify_token,
)

logger = logging.getLogger(__name__)


async def wx_login(code: str, db: AsyncSession, site_id: int = 1) -> Dict[str, Any]:
    """微信小程序登录

    流程：code → 调用微信 code2Session → 获取 openid/session_key → 查找或创建用户 → 生成 token

    Args:
        code: 微信登录临时凭证
        db: 数据库会话
        site_id: 营地ID，用于获取对应的微信 appid/secret

    Returns:
        包含 access_token, refresh_token, user_info 的字典
    """
    # 1. 调用微信 code2Session 接口
    openid, session_key = await _code2session(code, site_id)

    # 2. 查找或创建用户
    result = await db.execute(
        select(User).where(User.openid == openid, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if user is None:
        # 新用户注册
        user = User(
            openid=openid,
            status="active",
            role="user",
            member_level="normal",
            points_balance=0,
        )
        db.add(user)
        await db.flush()
        logger.info(f"[认证] 新用户注册: user_id={user.id}, openid={openid[:8]}...")

    # 3. 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)

    # 4. 生成 token
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": get_token_expire_seconds("access"),
        "user_info": {
            "id": user.id,
            "openid": user.openid,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "role": user.role,
            "is_member": user.is_member,
            "member_level": user.member_level,
            "points_balance": user.points_balance,
            "status": user.status,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
        },
    }


async def _code2session(code: str, site_id: int = 1) -> tuple[str, str]:
    """调用微信 code2Session 接口

    Args:
        code: 微信登录临时凭证
        site_id: 营地ID，用于获取对应的 appid/secret

    Returns:
        (openid, session_key)

    Raises:
        HTTPException: 微信API调用失败
    """
    # 根据 site_id 获取对应的微信配置
    app_id = settings.WECHAT_APP_ID
    app_secret = settings.WECHAT_APP_SECRET

    try:
        wechat_apps = json.loads(settings.WECHAT_APPS)
        if str(site_id) in wechat_apps:
            app_config = wechat_apps[str(site_id)]
            app_id = app_config.get("app_id", app_id)
            app_secret = app_config.get("app_secret", app_secret)
    except (json.JSONDecodeError, TypeError):
        pass  # 使用默认配置

    # 开发/测试环境：模拟登录
    if settings.APP_ENV in ("development", "testing") and (
        not app_id or app_id == ""
    ):
        logger.warning(f"[认证] 开发模式：使用模拟微信登录 (site_id={site_id})")
        return f"mock_openid_{code}_site{site_id}", "mock_session_key"

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": app_id,
        "secret": app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
    except Exception as e:
        logger.error(f"[认证] 微信API调用异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50002, "message": "微信API调用失败"},
        )

    if "errcode" in data and data["errcode"] != 0:
        logger.error(f"[认证] 微信API返回错误: {data}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50002, "message": f"微信登录失败: {data.get('errmsg', '')}"},
        )

    openid = data.get("openid")
    session_key = data.get("session_key", "")

    if not openid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50002, "message": "微信API未返回openid"},
        )

    return openid, session_key


async def admin_login(username: str, password: str, db: AsyncSession) -> Dict[str, Any]:
    """管理后台登录

    Args:
        username: 用户名
        password: 密码
        db: 数据库会话

    Returns:
        包含 access_token, refresh_token, admin_info 的字典

    Raises:
        HTTPException: 用户名或密码错误
    """
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.username == username,
            AdminUser.is_deleted.is_(False),
        )
    )
    admin = result.scalar_one_or_none()

    if admin is None or not admin.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "用户名或密码错误"},
        )

    if not verify_password(password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "用户名或密码错误"},
        )

    if admin.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": "管理员账号已被禁用"},
        )

    # 更新最后登录时间
    admin.last_login_at = datetime.now(timezone.utc)

    # 获取角色和权限信息
    role_code = admin.role.role_code if admin.role else None
    permissions = []
    if admin.role and admin.role.permissions:
        permissions = [f"{p.resource}:{p.action}" for p in admin.role.permissions]

    # 生成 token
    token_data = {
        "sub": f"admin:{admin.id}",
        "role": role_code or "staff",
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": get_token_expire_seconds("access"),
        "user": {
            "id": admin.id,
            "username": admin.username,
            "real_name": admin.real_name,
            "phone": admin.phone,
            "role": {
                "id": admin.role.id if admin.role else None,
                "role_name": admin.role.role_name if admin.role else None,
                "role_code": role_code,
                "description": admin.role.description if admin.role else None,
            },
            "status": admin.status,
            "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None,
        },
        "permissions": permissions,
    }


async def refresh_tokens(refresh_token_str: str, db: AsyncSession) -> Dict[str, Any]:
    """刷新 Token

    Args:
        refresh_token_str: refresh_token
        db: 数据库会话

    Returns:
        新的 access_token 和 refresh_token

    Raises:
        HTTPException: refresh_token 无效或过期
    """
    try:
        payload = verify_token(refresh_token_str)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40103, "message": "refresh_token无效或已过期"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "Token类型无效，需要refresh_token"},
        )

    sub = payload.get("sub", "")
    role = payload.get("role", "user")

    # 验证用户/管理员是否存在
    if sub.startswith("admin:"):
        admin_id = int(sub.replace("admin:", ""))
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.id == admin_id,
                AdminUser.is_deleted.is_(False),
            )
        )
        entity = result.scalar_one_or_none()
        if entity is None or entity.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": 40403, "message": "管理员不存在或已禁用"},
            )
    else:
        user_id = int(sub)
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_deleted.is_(False),
            )
        )
        entity = result.scalar_one_or_none()
        if entity is None or entity.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": 40403, "message": "用户不存在或已禁用"},
            )

    # 生成新 token
    token_data = {"sub": sub, "role": role}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "Bearer",
        "expires_in": get_token_expire_seconds("access"),
    }
