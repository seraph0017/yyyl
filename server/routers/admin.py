"""
管理后台路由

- GET /dashboard — Dashboard 概览
- GET /dashboard/trend — 趋势图
- GET /dashboard/sales-ranking — 销售排行
- GET /dashboard/heatmap — 热力图
- GET /users — 用户列表
- GET /members — 会员管理
- GET /logs — 操作日志
- GET /calendar — 营地日历
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from models.admin import AdminUser
from schemas.admin import (
    CalendarQuery,
    CalendarResponse,
    DashboardOverview,
    HeatmapDataResponse,
    OperationLogListParams,
    OperationLogResponse,
    SalesRankingItem,
    TrendDataResponse,
)
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel

router = APIRouter(prefix="/api/v1/admin", tags=["管理后台"])


# ========== Dashboard ==========

@router.get("/dashboard", summary="Dashboard 概览")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取管理后台 Dashboard 概览数据：今日订单/收入/在营人数/库存告警"""
    # TODO: dashboard_service.get_overview(db)
    return ResponseModel.success(data={
        "today_orders": 0,
        "today_revenue": "0.00",
        "today_visitors": 0,
        "inventory_alerts": 0,
        "yesterday_orders": 0,
        "yesterday_revenue": "0.00",
        "order_growth_rate": None,
        "revenue_growth_rate": None,
    })


@router.get("/dashboard/trend", summary="趋势图")
async def get_dashboard_trend(
    period: str = Query("7d", description="时间范围: 7d/30d"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取订单和收入趋势图数据"""
    # TODO: dashboard_service.get_trend(db, period)
    return ResponseModel.success(data={
        "period": period,
        "data": [],
    })


@router.get("/dashboard/sales-ranking", summary="销售排行")
async def get_sales_ranking(
    top: int = Query(10, ge=1, le=50, description="排名数量"),
    date_start: Optional[date] = Query(None, description="开始日期"),
    date_end: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取商品销售排行榜"""
    # TODO: dashboard_service.get_sales_ranking(db, top, date_start, date_end)
    return ResponseModel.success(data=[])


@router.get("/dashboard/heatmap", summary="营位预定热力图")
async def get_heatmap(
    date_start: date = Query(..., description="开始日期"),
    date_end: date = Query(..., description="结束日期"),
    product_ids: Optional[str] = Query(None, description="商品ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取营位预定热力图数据（日期×营位矩阵）"""
    # TODO: dashboard_service.get_heatmap(db, date_start, date_end, product_ids)
    return ResponseModel.success(data={
        "date_start": date_start,
        "date_end": date_end,
        "data": [],
    })


# ========== 用户管理 ==========

@router.get("/users", summary="用户列表")
async def list_users(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="用户状态"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端用户列表"""
    # TODO: user_service.list_users(db, keyword, status, pagination)
    return PaginatedResponse.create(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 会员管理 ==========

@router.get("/members", summary="会员管理")
async def list_members(
    member_level: Optional[str] = Query(None, description="会员等级"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端会员列表"""
    # TODO: member_service.list_members(db, member_level, pagination)
    return PaginatedResponse.create(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 操作日志 ==========

@router.get("/logs", summary="操作日志")
async def list_operation_logs(
    params: OperationLogListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """查询管理后台操作日志"""
    # TODO: admin_service.list_operation_logs(db, params, pagination)
    return PaginatedResponse.create(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 营地日历 ==========

@router.get("/calendar", summary="营地日历")
async def get_camp_calendar(
    date_start: date = Query(..., description="开始日期"),
    date_end: date = Query(..., description="结束日期"),
    product_ids: Optional[str] = Query(None, description="商品ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取营地日历数据：库存+价格+预定矩阵"""
    # TODO: admin_service.get_camp_calendar(db, date_start, date_end, product_ids)
    return ResponseModel.success(data={
        "date_start": date_start,
        "date_end": date_end,
        "cells": [],
    })
