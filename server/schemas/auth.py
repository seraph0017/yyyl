"""
认证相关 Schemas

- WxLoginRequest / WxLoginResponse：微信小程序登录
- AdminLoginRequest / AdminLoginResponse：管理后台登录
- TokenRefreshRequest / TokenRefreshResponse：Token 刷新
- TokenPayload：JWT 载荷模型
"""


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.user import UserInfo


# ---- 微信小程序登录 ----

class WxLoginRequest(BaseModel):
    """微信小程序登录请求"""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(min_length=1, description="微信登录临时凭证 code")


class WxLoginResponse(BaseModel):
    """微信登录响应"""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(description="access_token 有效期（秒）")
    user_info: UserInfo = Field(description="用户基本信息")


class PhoneLoginRequest(BaseModel):
    """微信手机号授权登录请求"""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(min_length=1, description="微信登录临时凭证 code")
    phone_code: str = Field(min_length=1, description="getPhoneNumber 获取的 code")


# ---- 管理后台登录 ----

class AdminLoginRequest(BaseModel):
    """管理后台账号密码登录请求"""

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(min_length=1, max_length=50, description="用户名")
    password: str = Field(min_length=6, max_length=128, description="密码")


class AdminLoginResponse(BaseModel):
    """管理后台登录响应"""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(description="access_token 有效期（秒）")
    admin_id: int = Field(description="管理员ID")
    username: str = Field(description="用户名")
    real_name: Optional[str] = Field(default=None, description="真实姓名")
    role_code: Optional[str] = Field(default=None, description="角色代码")
    permissions: list[str] = Field(default_factory=list, description="权限列表 ['product:read', ...]")


class AdminWxLoginRequest(BaseModel):
    """管理后台微信扫码登录请求"""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(min_length=1, description="微信登录code")


# ---- Token 操作 ----

class TokenRefreshRequest(BaseModel):
    """刷新 Token 请求"""

    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(min_length=1, description="刷新令牌")


class TokenRefreshResponse(BaseModel):
    """刷新 Token 响应"""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(description="新的访问令牌")
    refresh_token: str = Field(description="新的刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(description="access_token 有效期（秒）")


# ---- JWT 载荷 ----

class TokenPayload(BaseModel):
    """JWT Token 载荷模型"""

    model_config = ConfigDict(populate_by_name=True)

    sub: str = Field(description="主体标识（user_id 或 admin_id）")
    token_type: str = Field(description="令牌类型: access / refresh")
    role: str = Field(description="角色: user / staff / admin / super_admin")
    exp: datetime = Field(description="过期时间")
    iat: datetime = Field(description="签发时间")
    jti: Optional[str] = Field(default=None, description="Token唯一标识（用于黑名单）")
    site_id: int = Field(default=1, description="营地ID")
