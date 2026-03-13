"""
认证路由

- POST /wx-login — 微信小程序登录
- POST /admin-login — 管理后台登录
- POST /refresh — 刷新 Token
- GET /me — 当前用户信息
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from middleware.site import get_site_id
from models.user import User
from schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    PhoneLoginRequest,
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
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    微信小程序登录：前端传入 wx.login() 获取的 code，
    后端调用微信 code2Session 接口换取 openid，查找或创建用户并返回 Token。
    通过 X-Site-Id 请求头区分不同营地小程序。
    """
    site_id = get_site_id(request)
    result = await auth_service.wx_login(body.code, db, site_id=site_id)
    return ResponseModel.success(data=result)


@router.post("/login", summary="微信小程序登录（别名）")
async def wx_login_alias(
    body: WxLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """与 /wx-login 相同，兼容小程序端 POST /auth/login 调用"""
    site_id = get_site_id(request)
    result = await auth_service.wx_login(body.code, db, site_id=site_id)
    return ResponseModel.success(data=result)


@router.post("/phone-login", summary="微信手机号授权登录")
async def phone_login(
    body: PhoneLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    微信小程序手机号授权登录：先用 code 换 openid，
    再用 phone_code 调用微信 getPhoneNumber 接口获取手机号并绑定。
    通过 X-Site-Id 请求头区分不同营地小程序。
    """
    site_id = get_site_id(request)
    # 先走 wx_login 获取/创建用户
    result = await auth_service.wx_login(body.code, db, site_id=site_id)
    # TODO: 用 phone_code 调用微信 getPhoneNumber 接口获取手机号并绑定到用户
    # 目前先直接返回登录结果
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
