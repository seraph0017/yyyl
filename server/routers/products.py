"""
商品路由

C端 /api/v1/products：
- GET / — 商品列表
- GET /{id} — 商品详情
- GET /{id}/inventory — 库存查询
- GET /{id}/price-calendar — 价格日历

B端 /api/v1/admin/products：
- POST / — 创建商品
- PUT /{id} — 更新商品
- PATCH /{id}/status — 上架/下架
- POST /batch-status — 批量上架/下架
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin, get_optional_user
from models.admin import AdminUser
from models.user import User
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.product import (
    BatchStatusUpdate,
    InventoryQuery,
    InventoryResponse,
    PriceCalendarItem,
    ProductCreate,
    ProductDetail,
    ProductListItem,
    ProductSearchParams,
    ProductStatusUpdate,
    ProductUpdate,
)
from services import inventory_service, product_service

router = APIRouter(tags=["商品"])


# ========== C端接口 ==========

@router.get("/api/v1/products", summary="商品列表")
async def list_products(
    params: ProductSearchParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端商品列表，支持关键词搜索、类型/分类/价格筛选"""
    products, total = await product_service.list_products(
        db,
        keyword=params.keyword,
        product_type=params.type,
        category=params.category,
        product_status=params.status or "on_sale",
        min_price=params.min_price,
        max_price=params.max_price,
        is_seckill=params.is_seckill,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [ProductListItem.model_validate(p) for p in products]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/api/v1/products/{product_id}", summary="商品详情")
async def get_product_detail(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端获取商品详情（含扩展信息、定价规则、SKU列表）"""
    product = await product_service.get_product_detail(db, product_id)
    detail = ProductDetail.model_validate(product)
    return ResponseModel.success(data=detail)


@router.get("/api/v1/products/{product_id}/inventory", summary="商品库存查询")
async def get_product_inventory(
    product_id: int,
    date_start: Optional[date] = Query(None, description="起始日期"),
    date_end: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """查询指定商品的库存情况"""
    inventories, total = await inventory_service.query_inventory(
        db,
        product_id=product_id,
        date_start=date_start,
        date_end=date_end,
        inv_status="open",
    )
    items = [InventoryResponse.model_validate(inv) for inv in inventories]
    return ResponseModel.success(data=items)


@router.get("/api/v1/products/{product_id}/price-calendar", summary="价格日历")
async def get_price_calendar(
    product_id: int,
    date_start: date = Query(..., description="起始日期"),
    date_end: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取商品在日期区间内的价格和库存日历"""
    calendar = await product_service.get_price_calendar(
        db, product_id, date_start, date_end,
    )
    items = [PriceCalendarItem.model_validate(item) for item in calendar]
    return ResponseModel.success(data=items)


# ========== B端管理接口 ==========

@router.post("/api/v1/admin/products", summary="创建商品")
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端创建商品"""
    data = body.model_dump(exclude_none=True)
    product = await product_service.create_product(db, data, operator_id=admin.id)
    detail = ProductDetail.model_validate(product)
    return ResponseModel.success(data=detail, message="商品创建成功")


@router.put("/api/v1/admin/products/{product_id}", summary="更新商品")
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端更新商品信息"""
    data = body.model_dump(exclude_none=True)
    product = await product_service.update_product(db, product_id, data, operator_id=admin.id)
    detail = ProductDetail.model_validate(product)
    return ResponseModel.success(data=detail, message="商品更新成功")


@router.patch("/api/v1/admin/products/{product_id}/status", summary="上架/下架商品")
async def update_product_status(
    product_id: int,
    body: ProductStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端上架/下架商品"""
    product = await product_service.update_product_status(
        db, product_id, body.status, operator_id=admin.id,
    )
    return ResponseModel.success(
        data={"id": product.id, "status": product.status},
        message="状态更新成功",
    )


@router.post("/api/v1/admin/products/batch-status", summary="批量上架/下架")
async def batch_update_status(
    body: BatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端批量上架/下架商品"""
    count = await product_service.batch_update_status(
        db, body.product_ids, body.status, operator_id=admin.id,
    )
    return ResponseModel.success(
        data={"updated_count": count},
        message=f"批量操作完成，共更新 {count} 件商品",
    )
