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
from redis_client import get_redis
from utils.security import (
    create_access_token,
    create_refresh_token,
    get_token_expire_seconds,
    verify_password,
    verify_token,
)

logger = logging.getLogger(__name__)

WECHAT_API_BASE = "https://api.weixin.qq.com"


def _get_wechat_app_config(site_id: int) -> tuple[str, str]:
    """读取营地对应的微信小程序 AppID/Secret。"""
    app_id = settings.WECHAT_APP_ID
    app_secret = settings.WECHAT_APP_SECRET
    try:
        wechat_apps = json.loads(settings.WECHAT_APPS or "{}")
        site_config = wechat_apps.get(str(site_id)) or {}
        app_id = site_config.get("app_id") or app_id
        app_secret = site_config.get("app_secret") or app_secret
    except (json.JSONDecodeError, TypeError):
        pass
    return app_id, app_secret


def _serialize_user_login(user: User) -> Dict[str, Any]:
    """生成小程序登录响应中的用户信息。"""
    phone = user.phone
    if phone and len(phone) >= 11:
        phone = f"{phone[:3]}****{phone[-4:]}"
    return {
        "id": user.id,
        "openid": user.openid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "phone": phone,
        "role": user.role,
        "is_member": user.is_member,
        "member_level": user.member_level,
        "points_balance": user.points_balance,
        "status": user.status,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


def _build_user_login_response(user: User) -> Dict[str, Any]:
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": get_token_expire_seconds("access"),
        "user_info": _serialize_user_login(user),
    }


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
    user.last_login_at = datetime.utcnow()

    # 4. 生成 token
    return _build_user_login_response(user)

async def phone_login(
    code: str,
    phone_code: str,
    db: AsyncSession,
    site_id: int = 1,
) -> Dict[str, Any]:
    """微信手机号授权登录：换取 openid 后调用 getPhoneNumber 并绑定手机号。"""
    openid, _session_key = await _code2session(code, site_id)
    phone_number = await _get_phone_number(phone_code, site_id=site_id)

    result = await db.execute(
        select(User).where(User.openid == openid, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            openid=openid,
            phone=phone_number,
            status="active",
            role="user",
            member_level="normal",
            points_balance=0,
            site_id=site_id,
        )
        db.add(user)
        await db.flush()
        logger.info(f"[认证] 手机号授权新用户注册: user_id={user.id}, openid={openid[:8]}...")
    else:
        user.phone = phone_number
        user.site_id = getattr(user, "site_id", site_id) or site_id

    user.last_login_at = datetime.utcnow()
    await db.flush()
    return _build_user_login_response(user)


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
    app_id, app_secret = _get_wechat_app_config(site_id)

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
        logger.error(
            "[认证] 微信API返回错误: site=%s errcode=%s errmsg=%s",
            site_id,
            data.get("errcode"),
            data.get("errmsg", ""),
        )
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


async def _get_phone_number(phone_code: str, *, site_id: int = 1) -> str:
    """调用微信 getPhoneNumber 接口获取授权手机号。"""
    access_token = await _get_wechat_access_token(site_id)
    url = f"{WECHAT_API_BASE}/wxa/business/getuserphonenumber?access_token={access_token}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"code": phone_code})
            data = resp.json()
    except Exception as exc:
        logger.error(f"[认证] 微信手机号接口调用异常: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50003, "message": "微信手机号授权失败"},
        )

    if data.get("errcode", 0) != 0:
        logger.error(
            "[认证] 微信手机号接口返回错误: site=%s errcode=%s errmsg=%s",
            site_id,
            data.get("errcode"),
            data.get("errmsg", ""),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50003, "message": f"微信手机号授权失败: {data.get('errmsg', '')}"},
        )

    phone_info = data.get("phone_info") or {}
    phone_number = phone_info.get("phoneNumber") or phone_info.get("purePhoneNumber")
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50003, "message": "微信手机号授权未返回手机号"},
        )
    return phone_number


async def _get_wechat_access_token(site_id: int) -> str:
    """获取微信 access_token，用于手机号授权接口。"""
    cache_key = f"wechat:access_token:{site_id}"
    redis = None
    try:
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return cached
    except RuntimeError:
        redis = None

    app_id, app_secret = _get_wechat_app_config(site_id)
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 50004, "message": "微信小程序配置缺失"},
        )

    url = (
        f"{WECHAT_API_BASE}/cgi-bin/token"
        f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            payload = response.json()
    except Exception as exc:
        logger.error(f"[认证] 微信 access_token 获取异常: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50004, "message": "微信 access_token 获取失败"},
        )

    access_token = payload.get("access_token")
    if not access_token:
        logger.error(
            "[认证] 微信 access_token 返回错误: site=%s errcode=%s errmsg=%s",
            site_id,
            payload.get("errcode"),
            payload.get("errmsg", ""),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50004, "message": "微信 access_token 获取失败"},
        )

    if redis is not None:
        expires_in = int(payload.get("expires_in") or 7200)
        await redis.setex(cache_key, max(expires_in - 300, 60), access_token)
    return access_token


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
    admin.last_login_at = datetime.utcnow()

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
