"""
搭配售卖路由

C端：
- GET  /api/v1/products/{product_id}/bundles       — 获取商品搭配推荐（🌐 游客可访问）
- GET  /api/v1/orders/{order_id}/available-bundles  — 获取订单可追加搭配（👤 用户）
- POST /api/v1/orders/{order_id}/bundle-addons      — 追加搭配下单（👤 用户）

B端：
- GET    /api/v1/admin/bundle-configs                — 搭配组合列表（🔑 管理员）
- POST   /api/v1/admin/bundle-configs                — 创建搭配组合
- PUT    /api/v1/admin/bundle-configs/{config_id}    — 更新搭配组合
- DELETE /api/v1/admin/bundle-configs/{config_id}    — 删除搭配组合
- GET    /api/v1/admin/reports/bundle-stats           — 搭配售卖统计
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin, get_current_user, get_optional_user
from middleware.site import get_site_id
from models.admin import AdminUser
from models.user import User
from schemas.bundle import (
    BundleConfigCreate,
    BundleConfigResponse,
    BundleConfigUpdate,
    BundleRecommendItem,
    BundleStatsResponse,
)
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from services import bundle_service

router = APIRouter(tags=["搭配售卖"])


# ========== C端接口 ==========


@router.get("/api/v1/products/{product_id}/bundles", summary="获取商品搭配推荐")
async def get_product_bundles(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端获取商品的搭配推荐列表（游客可访问）"""
    site_id = get_site_id(request)
    items = await bundle_service.get_product_bundles(
        db, product_id=product_id, site_id=site_id,
    )
    recommend_items = [BundleRecommendItem.model_validate(item) for item in items]
    return ResponseModel.success(data=recommend_items)


@router.get("/api/v1/orders/{order_id}/available-bundles", summary="获取订单可追加搭配")
async def get_order_available_bundles(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取已支付订单可追加的搭配商品列表"""
    site_id = get_site_id(request)
    # TODO: 根据订单主商品查询可追加的搭配，排除已选搭配
    items = await bundle_service.get_product_bundles(
        db, product_id=0, site_id=site_id,  # 将由 service 层根据 order_id 查询主商品
    )
    recommend_items = [BundleRecommendItem.model_validate(item) for item in items]
    return ResponseModel.success(data=recommend_items)


@router.post("/api/v1/orders/{order_id}/bundle-addons", summary="追加搭配下单")
async def add_bundle_to_order(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """在已支付订单基础上追加搭配商品，生成追加订单"""
    site_id = get_site_id(request)
    # TODO: 实现追加搭配下单逻辑（生成子订单/追加订单项）
    return ResponseModel.success(data=None, message="追加搭配下单功能开发中")


# ========== B端接口 ==========


@router.get("/api/v1/admin/bundle-configs", summary="搭配组合列表")
async def list_bundle_configs(
    request: Request,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """B端搭配组合列表，支持分页"""
    site_id = get_site_id(request)
    configs, total = await bundle_service.list_bundle_configs(
        db,
        site_id=site_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [BundleConfigResponse.model_validate(c) for c in configs]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/api/v1/admin/bundle-configs", summary="创建搭配组合")
async def create_bundle_config(
    body: BundleConfigCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建搭配组合配置"""
    site_id = get_site_id(request)
    config = await bundle_service.create_bundle_config(
        db,
        data=body.model_dump(),
        site_id=site_id,
    )
    await db.commit()
    result = BundleConfigResponse.model_validate(config)
    return ResponseModel.success(data=result, message="搭配组合创建成功")


@router.put("/api/v1/admin/bundle-configs/{config_id}", summary="更新搭配组合")
async def update_bundle_config(
    config_id: int,
    body: BundleConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新搭配组合配置"""
    site_id = get_site_id(request)
    config = await bundle_service.update_bundle_config(
        db,
        config_id=config_id,
        data=body.model_dump(exclude_unset=True),
        site_id=site_id,
    )
    await db.commit()
    result = BundleConfigResponse.model_validate(config)
    return ResponseModel.success(data=result, message="搭配组合更新成功")


@router.delete("/api/v1/admin/bundle-configs/{config_id}", summary="删除搭配组合")
async def delete_bundle_config(
    config_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除搭配组合（软删除）"""
    site_id = get_site_id(request)
    await bundle_service.delete_bundle_config(
        db,
        config_id=config_id,
        site_id=site_id,
    )
    await db.commit()
    return ResponseModel.success(message="搭配组合已删除")


@router.get("/api/v1/admin/reports/bundle-stats", summary="搭配售卖统计")
async def get_bundle_stats(
    request: Request,
    start_date: Optional[date] = Query(default=None, description="开始日期"),
    end_date: Optional[date] = Query(default=None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """B端搭配售卖统计数据"""
    site_id = get_site_id(request)
    stats = await bundle_service.get_bundle_stats(
        db,
        site_id=site_id,
        start_date=start_date,
        end_date=end_date,
    )
    result = BundleStatsResponse.model_validate(stats)
    return ResponseModel.success(data=result)
