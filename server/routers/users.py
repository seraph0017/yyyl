"""
用户路由

- GET /me — 用户信息
- PUT /me — 更新用户信息
- GET /identities — 身份列表
- POST /identities — 添加身份
- PUT /identities/{id} — 更新身份
- DELETE /identities/{id} — 删除身份
- GET /addresses — 地址列表
- POST /addresses — 添加地址
- PUT /addresses/{id} — 更新地址
- DELETE /addresses/{id} — 删除地址
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.user import User, UserAddress, UserIdentity
from schemas.common import ResponseModel
from schemas.user import (
    UserAddressCreate,
    UserAddressResponse,
    UserAddressUpdate,
    UserIdentityCreate,
    UserIdentityResponse,
    UserIdentityUpdate,
    UserInfo,
    UserProfileUpdate,
)

router = APIRouter(prefix="/api/v1/users", tags=["用户"])


# ========== 用户信息 ==========

@router.get("/me", summary="用户信息")
async def get_user_info(
    user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    result = UserInfo.model_validate(user)
    return ResponseModel.success(data=result)


@router.put("/me", summary="更新用户信息")
async def update_user_info(
    body: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新当前用户信息（昵称、头像等）"""
    if body.nickname is not None:
        user.nickname = body.nickname
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    await db.flush()
    result = UserInfo.model_validate(user)
    return ResponseModel.success(data=result, message="用户信息已更新")


# ========== 出行人身份信息 ==========

@router.get("/identities", summary="身份列表")
async def list_identities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的出行人身份信息列表"""
    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.user_id == user.id,
            UserIdentity.is_deleted.is_(False),
        ).order_by(UserIdentity.is_self.desc(), UserIdentity.created_at.desc())
    )
    identities = list(result.scalars().all())
    items = [UserIdentityResponse.model_validate(i) for i in identities]
    return ResponseModel.success(data=items)


@router.post("/identities", summary="添加身份")
async def create_identity(
    body: UserIdentityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """添加出行人身份信息"""
    identity = UserIdentity(
        user_id=user.id,
        name=body.name,
        id_card=body.id_card,
        phone=body.phone,
        custom_fields=body.custom_fields,
        is_self=body.is_self,
    )
    db.add(identity)
    await db.flush()
    result = UserIdentityResponse.model_validate(identity)
    return ResponseModel.success(data=result, message="身份信息已添加")


@router.put("/identities/{identity_id}", summary="更新身份")
async def update_identity(
    identity_id: int,
    body: UserIdentityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新出行人身份信息"""
    identity = await _get_user_identity(db, identity_id, user.id)

    if body.name is not None:
        identity.name = body.name
    if body.id_card is not None:
        identity.id_card = body.id_card
    if body.phone is not None:
        identity.phone = body.phone
    if body.custom_fields is not None:
        identity.custom_fields = body.custom_fields
    if body.is_self is not None:
        identity.is_self = body.is_self

    await db.flush()
    result = UserIdentityResponse.model_validate(identity)
    return ResponseModel.success(data=result, message="身份信息已更新")


@router.delete("/identities/{identity_id}", summary="删除身份")
async def delete_identity(
    identity_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除出行人身份信息（软删除）"""
    identity = await _get_user_identity(db, identity_id, user.id)
    identity.is_deleted = True
    await db.flush()
    return ResponseModel.success(message="身份信息已删除")


# ========== 收货地址 ==========

@router.get("/addresses", summary="地址列表")
async def list_addresses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的收货地址列表"""
    result = await db.execute(
        select(UserAddress).where(
            UserAddress.user_id == user.id,
            UserAddress.is_deleted.is_(False),
        ).order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
    )
    addresses = list(result.scalars().all())
    items = [UserAddressResponse.model_validate(a) for a in addresses]
    return ResponseModel.success(data=items)


@router.post("/addresses", summary="添加地址")
async def create_address(
    body: UserAddressCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """添加收货地址"""
    # 如果设为默认，先取消其他默认地址
    if body.is_default:
        await _clear_default_address(db, user.id)

    address = UserAddress(
        user_id=user.id,
        contact_name=body.contact_name,
        contact_phone=body.contact_phone,
        province=body.province,
        city=body.city,
        district=body.district,
        detail=body.detail,
        is_default=body.is_default,
    )
    db.add(address)
    await db.flush()
    result = UserAddressResponse.model_validate(address)
    return ResponseModel.success(data=result, message="地址已添加")


@router.put("/addresses/{address_id}", summary="更新地址")
async def update_address(
    address_id: int,
    body: UserAddressUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新收货地址"""
    address = await _get_user_address(db, address_id, user.id)

    if body.is_default:
        await _clear_default_address(db, user.id)

    if body.contact_name is not None:
        address.contact_name = body.contact_name
    if body.contact_phone is not None:
        address.contact_phone = body.contact_phone
    if body.province is not None:
        address.province = body.province
    if body.city is not None:
        address.city = body.city
    if body.district is not None:
        address.district = body.district
    if body.detail is not None:
        address.detail = body.detail
    if body.is_default is not None:
        address.is_default = body.is_default

    await db.flush()
    result = UserAddressResponse.model_validate(address)
    return ResponseModel.success(data=result, message="地址已更新")


@router.delete("/addresses/{address_id}", summary="删除地址")
async def delete_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除收货地址（软删除）"""
    address = await _get_user_address(db, address_id, user.id)
    address.is_deleted = True
    await db.flush()
    return ResponseModel.success(message="地址已删除")


# ---- 内部方法 ----

async def _get_user_identity(
    db: AsyncSession, identity_id: int, user_id: int,
) -> UserIdentity:
    """获取用户的身份信息（带权限校验）"""
    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.id == identity_id,
            UserIdentity.user_id == user_id,
            UserIdentity.is_deleted.is_(False),
        )
    )
    identity = result.scalar_one_or_none()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "身份信息不存在"},
        )
    return identity


async def _get_user_address(
    db: AsyncSession, address_id: int, user_id: int,
) -> UserAddress:
    """获取用户的收货地址（带权限校验）"""
    result = await db.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id,
            UserAddress.is_deleted.is_(False),
        )
    )
    address = result.scalar_one_or_none()
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "地址不存在"},
        )
    return address


async def _clear_default_address(db: AsyncSession, user_id: int) -> None:
    """取消用户的所有默认地址"""
    result = await db.execute(
        select(UserAddress).where(
            UserAddress.user_id == user_id,
            UserAddress.is_default.is_(True),
            UserAddress.is_deleted.is_(False),
        )
    )
    for addr in result.scalars().all():
        addr.is_default = False
