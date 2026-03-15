"""
绩效路由（全部 B 端）

- GET  /api/v1/admin/performance/configs   — 绩效系数配置列表
- PUT  /api/v1/admin/performance/configs   — 更新绩效系数
- GET  /api/v1/admin/performance/records   — 绩效记录列表
- GET  /api/v1/admin/performance/ranking   — 绩效排名
- POST /api/v1/admin/performance/calculate — 触发绩效计算
- POST /api/v1/admin/performance/export    — 导出绩效报表
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.performance import (
    PerformanceCalculateRequest,
    PerformanceConfigResponse,
    PerformanceConfigUpdate,
    PerformanceRankingItem,
    PerformanceRecordResponse,
)
from services import performance_service

router = APIRouter(tags=["绩效管理"])


# ========== 绩效系数配置 ==========


@router.get("/api/v1/admin/performance/configs", summary="绩效系数配置列表")
async def list_performance_configs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取绩效系数配置列表"""
    site_id = get_site_id(request)
    configs = await performance_service.get_performance_configs(
        db, site_id=site_id,
    )
    items = [PerformanceConfigResponse.model_validate(c) for c in configs]
    return ResponseModel.success(data=items)


@router.put("/api/v1/admin/performance/configs", summary="更新绩效系数")
async def update_performance_configs(
    body: PerformanceConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """批量更新绩效系数配置（upsert 语义）"""
    site_id = get_site_id(request)
    configs = await performance_service.update_performance_configs(
        db,
        configs=[c.model_dump() for c in body.configs],
        site_id=site_id,
    )
    await db.commit()
    items = [PerformanceConfigResponse.model_validate(c) for c in configs]
    return ResponseModel.success(data=items, message="绩效系数更新成功")


# ========== 绩效记录 ==========


@router.get("/api/v1/admin/performance/records", summary="绩效记录列表")
async def list_performance_records(
    request: Request,
    pagination: PaginationParams = Depends(),
    staff_user_id: Optional[int] = Query(
        default=None, description="员工ID筛选",
    ),
    period_type: Optional[str] = Query(
        default=None, description="周期类型: daily/weekly/monthly",
    ),
    period_start: Optional[date] = Query(
        default=None, description="周期开始日期",
    ),
    period_end: Optional[date] = Query(
        default=None, description="周期结束日期",
    ),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """绩效记录列表，支持按员工/周期类型/日期筛选"""
    site_id = get_site_id(request)
    records, total = await performance_service.list_performance_records(
        db,
        site_id=site_id,
        staff_user_id=staff_user_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [PerformanceRecordResponse.model_validate(r) for r in records]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 绩效排名 ==========


@router.get("/api/v1/admin/performance/ranking", summary="绩效排名")
async def get_performance_ranking(
    request: Request,
    period_type: str = Query(
        default="monthly", description="周期类型: daily/weekly/monthly",
    ),
    period_start: Optional[date] = Query(
        default=None, description="周期开始日期（默认当月1号）",
    ),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """绩效排名（按总绩效降序）"""
    site_id = get_site_id(request)
    ranking = await performance_service.get_performance_ranking(
        db,
        site_id=site_id,
        period_type=period_type,
        period_start=period_start,
    )
    items = [PerformanceRankingItem.model_validate(r) for r in ranking]
    return ResponseModel.success(data=items)


# ========== 绩效计算 ==========


@router.post("/api/v1/admin/performance/calculate", summary="触发绩效计算")
async def calculate_performance(
    body: PerformanceCalculateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """手动触发绩效计算

    根据订单数据和绩效系数配置，计算指定周期内各员工的绩效。
    """
    site_id = get_site_id(request)
    records = await performance_service.calculate_performance(
        db,
        site_id=site_id,
        period_type=body.period_type,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    await db.commit()
    items = [PerformanceRecordResponse.model_validate(r) for r in records]
    return ResponseModel.success(
        data=items,
        message=f"绩效计算完成，共 {len(items)} 名员工",
    )


# ========== 绩效导出 ==========


@router.post("/api/v1/admin/performance/export", summary="导出绩效报表")
async def export_performance(
    request: Request,
    period_type: str = Query(
        default="monthly", description="周期类型: daily/weekly/monthly",
    ),
    period_start: Optional[date] = Query(
        default=None, description="周期开始日期",
    ),
    period_end: Optional[date] = Query(
        default=None, description="周期结束日期",
    ),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """导出绩效报表

    TODO: 实现 Excel 文件生成，返回下载链接
    """
    site_id = get_site_id(request)
    # 先获取记录数据
    records, total = await performance_service.list_performance_records(
        db,
        site_id=site_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        page=1,
        page_size=1000,  # 导出时获取所有数据
    )
    return ResponseModel.success(
        data={"total_records": total},
        message="导出功能开发中，后续将返回 Excel 下载链接",
    )
