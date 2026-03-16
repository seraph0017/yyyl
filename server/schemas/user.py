"""
用户相关 Schemas

- UserInfo：用户基本信息
- UserProfileUpdate：更新用户信息
- UserIdentityCreate/Update/Response：出行人身份信息 CRUD
- UserAddressCreate/Update/Response：收货地址 CRUD
"""


import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 用户基本信息 ----

class UserInfo(BaseModel):
    """用户基本信息（通用返回）"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="用户ID")
    openid: str = Field(description="微信OpenID")
    nickname: Optional[str] = Field(default=None, description="昵称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    phone: Optional[str] = Field(default=None, description="手机号（脱敏）")
    role: str = Field(description="角色: user/staff/admin")
    is_member: bool = Field(description="是否会员")
    member_level: str = Field(description="会员等级: normal/silver/gold/platinum")
    points_balance: int = Field(description="积分余额")
    status: str = Field(description="用户状态: active/disabled/deleted")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")
    created_at: datetime = Field(description="注册时间")

    @field_validator("phone", mode="before")
    @classmethod
    def mask_phone(cls, v: Optional[str]) -> Optional[str]:
        """手机号脱敏：138****1234"""
        if v and len(v) >= 11:
            return f"{v[:3]}****{v[-4:]}"
        return v


class UserProfileUpdate(BaseModel):
    """更新用户信息（昵称、头像）"""

    model_config = ConfigDict(populate_by_name=True)

    nickname: Optional[str] = Field(default=None, max_length=64, description="昵称")
    avatar_url: Optional[str] = Field(default=None, max_length=512, description="头像URL")


class UserPhoneRequest(BaseModel):
    """微信手机号授权请求"""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(min_length=1, description="微信手机号授权code")


# ---- 出行人身份信息 ----

class UserIdentityBase(BaseModel):
    """出行人身份信息基础字段"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=50, description="姓名")
    id_card: Optional[str] = Field(default=None, description="身份证号")
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    custom_fields: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="自定义字段 [{field_id, field_name, value}]",
    )

    @field_validator("id_card", mode="before")
    @classmethod
    def validate_id_card(cls, v: Optional[str]) -> Optional[str]:
        """校验身份证号格式（18位）"""
        if v is not None:
            v = v.strip()
            pattern = r"^\d{17}[\dXx]$"
            if not re.match(pattern, v):
                raise ValueError("身份证号格式不正确，应为18位")
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """校验手机号格式"""
        if v is not None:
            v = v.strip()
            if not re.match(r"^1[3-9]\d{9}$", v):
                raise ValueError("手机号格式不正确")
        return v


class UserIdentityCreate(UserIdentityBase):
    """新增出行人身份信息"""

    is_self: bool = Field(default=False, description="是否本人")
    is_default: bool = Field(default=False, description="是否默认出行人")


class UserIdentityUpdate(UserIdentityBase):
    """更新出行人身份信息"""

    is_self: Optional[bool] = Field(default=None, description="是否本人")
    is_default: Optional[bool] = Field(default=None, description="是否默认出行人")


class UserIdentityResponse(BaseModel):
    """出行人身份信息响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="身份信息ID")
    user_id: int = Field(description="用户ID")
    name: Optional[str] = Field(default=None, description="姓名")
    id_card_masked: Optional[str] = Field(default=None, description="身份证号（脱敏）")
    phone: Optional[str] = Field(default=None, description="手机号（脱敏）")
    custom_fields: Optional[List[Dict[str, Any]]] = Field(default=None, description="自定义字段")
    is_self: bool = Field(description="是否本人")
    is_default: bool = Field(description="是否默认出行人")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    @field_validator("phone", mode="before")
    @classmethod
    def mask_phone(cls, v: Optional[str]) -> Optional[str]:
        """手机号脱敏"""
        if v and len(v) >= 11:
            return f"{v[:3]}****{v[-4:]}"
        return v


# ---- 收货地址 ----

class UserAddressBase(BaseModel):
    """收货地址基础字段"""

    model_config = ConfigDict(populate_by_name=True)

    contact_name: str = Field(min_length=1, max_length=50, description="收货人姓名")
    contact_phone: str = Field(min_length=11, max_length=20, description="手机号")
    province: str = Field(min_length=1, max_length=30, description="省")
    city: str = Field(min_length=1, max_length=30, description="市")
    district: str = Field(min_length=1, max_length=30, description="区")
    detail: str = Field(min_length=1, max_length=200, description="详细地址")
    is_default: bool = Field(default=False, description="是否默认地址")

    @field_validator("contact_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """校验手机号格式"""
        v = v.strip()
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class UserAddressCreate(UserAddressBase):
    """新增收货地址"""
    pass


class UserAddressUpdate(BaseModel):
    """更新收货地址（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    contact_name: Optional[str] = Field(default=None, max_length=50, description="收货人姓名")
    contact_phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    province: Optional[str] = Field(default=None, max_length=30, description="省")
    city: Optional[str] = Field(default=None, max_length=30, description="市")
    district: Optional[str] = Field(default=None, max_length=30, description="区")
    detail: Optional[str] = Field(default=None, max_length=200, description="详细地址")
    is_default: Optional[bool] = Field(default=None, description="是否默认地址")

    @field_validator("contact_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not re.match(r"^1[3-9]\d{9}$", v):
                raise ValueError("手机号格式不正确")
        return v


class UserAddressResponse(BaseModel):
    """收货地址响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="地址ID")
    user_id: int = Field(description="用户ID")
    contact_name: str = Field(description="收货人姓名")
    contact_phone: str = Field(description="手机号（脱敏）")
    province: str = Field(description="省")
    city: str = Field(description="市")
    district: str = Field(description="区")
    detail: str = Field(description="详细地址")
    is_default: bool = Field(description="是否默认")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    @field_validator("contact_phone", mode="before")
    @classmethod
    def mask_phone(cls, v: str) -> str:
        """手机号脱敏"""
        if v and len(v) >= 11:
            return f"{v[:3]}****{v[-4:]}"
        return v


# ---- 免责声明 ----

class DisclaimerSignRequest(BaseModel):
    """签署免责声明请求"""

    model_config = ConfigDict(populate_by_name=True)

    order_id: int = Field(description="订单ID")
    template_id: int = Field(description="免责声明模板ID")


class DisclaimerStatusResponse(BaseModel):
    """免责声明签署状态"""

    model_config = ConfigDict(populate_by_name=True)

    signed: bool = Field(description="是否已签署")
    signed_at: Optional[datetime] = Field(default=None, description="签署时间")
    template_id: Optional[int] = Field(default=None, description="模板ID")
    template_version: Optional[int] = Field(default=None, description="模板版本")
