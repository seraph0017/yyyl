"""
购物车路由

- GET / — 购物车列表
- POST /items — 添加商品
- PUT /items/{id} — 修改数量
- DELETE /items/{id} — 删除商品
- POST /checkout — 结算
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.common import ResponseModel

router = APIRouter(prefix="/api/v1/cart", tags=["购物车"])


@router.get("/", summary="购物车列表")
async def list_cart_items(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的购物车列表"""
    # TODO: cart_service.list_cart_items(db, user.id)
    return ResponseModel.success(data=[])


@router.post("/items", summary="添加商品到购物车")
async def add_cart_item(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """添加商品到购物车"""
    # TODO: cart_service.add_item(db, user.id, body)
    return ResponseModel.success(data=None, message="已添加到购物车")


@router.put("/items/{item_id}", summary="修改购物车商品数量")
async def update_cart_item(
    item_id: int,
    quantity: int = Body(..., ge=1, embed=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修改购物车中商品的数量"""
    # TODO: cart_service.update_item(db, user.id, item_id, quantity)
    return ResponseModel.success(data=None, message="数量已更新")


@router.delete("/items/{item_id}", summary="删除购物车商品")
async def delete_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从购物车中删除商品"""
    # TODO: cart_service.delete_item(db, user.id, item_id)
    return ResponseModel.success(data=None, message="已从购物车移除")


@router.post("/checkout", summary="购物车结算")
async def checkout(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """购物车结算：生成预订单"""
    # TODO: cart_service.checkout(db, user.id, body)
    return ResponseModel.success(data=None, message="结算完成")
