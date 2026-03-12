"""
认证路由

- POST /wx-login — 微信小程序登录
- POST /admin-login — 管理后台登录
- POST /refresh — 刷新 Token
- GET /me — 当前用户信息
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    WxLoginRequest,
    WxLoginResponse,
)
from schemas.common import ResponseModel
from schemas.user import UserInfo
from services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/wx-login", summary="微信小程序登录")
async def wx_login(
    body: WxLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    微信小程序登录：前端传入 wx.login() 获取的 code，
    后端调用微信 code2Session 接口换取 openid，查找或创建用户并返回 Token。
    """
    result = await auth_service.wx_login(body.code, db)
    return ResponseModel.success(data=result)


@router.post("/admin-login", summary="管理后台登录")
async def admin_login(
    body: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """管理后台账号密码登录"""
    result = await auth_service.admin_login(body.username, body.password, db)
    return ResponseModel.success(data=result)


@router.post("/refresh", summary="刷新Token")
async def refresh_token(
    body: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """使用 refresh_token 获取新的 access_token 和 refresh_token"""
    result = await auth_service.refresh_tokens(body.refresh_token, db)
    return ResponseModel.success(data=result)


@router.get("/me", summary="当前用户信息")
async def get_me(
    user: User = Depends(get_current_user),
):
    """获取当前登录用户的基本信息"""
    user_info = UserInfo.model_validate(user)
    return ResponseModel.success(data=user_info)
