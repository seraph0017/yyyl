"""
报销路由（全部 B 端）

- GET/POST  /api/v1/admin/expense-types                    — 报销类型列表/创建
- PUT       /api/v1/admin/expense-types/{type_id}          — 更新报销类型
- GET/POST  /api/v1/admin/expenses                         — 报销申请列表/提交
- GET       /api/v1/admin/expenses/{expense_id}            — 报销详情
- POST      /api/v1/admin/expenses/{expense_id}/approve    — 审批
- POST      /api/v1/admin/expenses/{expense_id}/mark-paid  — 标记打款
- GET       /api/v1/admin/expenses/stats                   — 报销统计
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.expense import (
    ExpenseApproveRequest,
    ExpenseRequestCreate,
    ExpenseRequestResponse,
    ExpenseStatsResponse,
    ExpenseTypeCreate,
    ExpenseTypeResponse,
    ExpenseTypeUpdate,
)
from services import expense_service

router = APIRouter(tags=["报销管理"])


# ========== 报销类型管理 ==========


@router.get("/api/v1/admin/expense-types", summary="报销类型列表")
async def list_expense_types(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取报销类型列表"""
    site_id = get_site_id(request)
    types = await expense_service.list_expense_types(db, site_id=site_id)
    items = [ExpenseTypeResponse.model_validate(t) for t in types]
    return ResponseModel.success(data=items)


@router.post("/api/v1/admin/expense-types", summary="创建报销类型")
async def create_expense_type(
    body: ExpenseTypeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建报销类型"""
    site_id = get_site_id(request)
    expense_type = await expense_service.create_expense_type(
        db,
        data=body.model_dump(),
        site_id=site_id,
    )
    await db.commit()
    result = ExpenseTypeResponse.model_validate(expense_type)
    return ResponseModel.success(data=result, message="报销类型创建成功")


@router.put("/api/v1/admin/expense-types/{type_id}", summary="更新报销类型")
async def update_expense_type(
    type_id: int,
    body: ExpenseTypeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新报销类型"""
    site_id = get_site_id(request)
    expense_type = await expense_service.update_expense_type(
        db,
        type_id=type_id,
        data=body.model_dump(exclude_unset=True),
        site_id=site_id,
    )
    await db.commit()
    result = ExpenseTypeResponse.model_validate(expense_type)
    return ResponseModel.success(data=result, message="报销类型更新成功")


# ========== 报销申请管理 ==========


@router.get("/api/v1/admin/expenses", summary="报销申请列表")
async def list_expenses(
    request: Request,
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(
        default=None, description="状态筛选: pending/approved/rejected/paid",
    ),
    expense_type_id: Optional[int] = Query(
        default=None, description="报销类型ID",
    ),
    user_id: Optional[int] = Query(
        default=None, description="报销人ID",
    ),
    date_start: Optional[date] = Query(
        default=None, description="费用开始日期",
    ),
    date_end: Optional[date] = Query(
        default=None, description="费用结束日期",
    ),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """报销申请列表，支持按状态/类型/人员/日期筛选"""
    site_id = get_site_id(request)
    expenses, total = await expense_service.list_expenses(
        db,
        site_id=site_id,
        page=pagination.page,
        page_size=pagination.page_size,
        expense_status=status,
        expense_type_id=expense_type_id,
        user_id=user_id,
        date_start=date_start,
        date_end=date_end,
    )
    items = [ExpenseRequestResponse.model_validate(e) for e in expenses]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/api/v1/admin/expenses", summary="提交报销申请")
async def create_expense(
    body: ExpenseRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """提交报销申请（由管理员提交，报销人为当前管理员）"""
    site_id = get_site_id(request)
    expense = await expense_service.create_expense_request(
        db,
        user_id=admin.id,
        data=body.model_dump(),
        site_id=site_id,
    )
    await db.commit()
    result = ExpenseRequestResponse.model_validate(expense)
    return ResponseModel.success(data=result, message="报销申请提交成功")


@router.get("/api/v1/admin/expenses/stats", summary="报销统计")
async def get_expense_stats(
    request: Request,
    year: Optional[int] = Query(default=None, description="年份"),
    month: Optional[int] = Query(default=None, ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """报销统计：总金额、当月总金额、按类型/员工统计"""
    site_id = get_site_id(request)
    stats = await expense_service.get_expense_stats(
        db,
        site_id=site_id,
        year=year,
        month=month,
    )
    result = ExpenseStatsResponse.model_validate(stats)
    return ResponseModel.success(data=result)


@router.get("/api/v1/admin/expenses/{expense_id}", summary="报销详情")
async def get_expense_detail(
    expense_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取报销申请详情"""
    site_id = get_site_id(request)
    expenses, _ = await expense_service.list_expenses(
        db,
        site_id=site_id,
        page=1,
        page_size=1,
    )
    # 通过 ID 精确查询
    from sqlalchemy import select
    from models.expense import ExpenseRequest as ExpenseRequestModel

    result = await db.execute(
        select(ExpenseRequestModel).where(
            ExpenseRequestModel.id == expense_id,
            ExpenseRequestModel.site_id == site_id,
            ExpenseRequestModel.is_deleted.is_(False),
        )
    )
    expense = result.scalar_one_or_none()

    if expense is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "报销申请不存在"},
        )

    resp = ExpenseRequestResponse.model_validate(expense)
    return ResponseModel.success(data=resp)


@router.post(
    "/api/v1/admin/expenses/{expense_id}/approve",
    summary="审批报销",
)
async def approve_expense(
    expense_id: int,
    body: ExpenseApproveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """审批报销申请

    业务规则：
    - 不允许自审
    - 金额 >= 1000 元需 super_admin 审批
    """
    site_id = get_site_id(request)
    expense = await expense_service.approve_expense(
        db,
        expense_id=expense_id,
        admin_id=admin.id,
        approved=body.approved,
        review_remark=body.review_remark,
        site_id=site_id,
    )
    await db.commit()
    result = ExpenseRequestResponse.model_validate(expense)
    status_text = "已通过" if body.approved else "已驳回"
    return ResponseModel.success(data=result, message=f"报销申请{status_text}")


@router.post(
    "/api/v1/admin/expenses/{expense_id}/mark-paid",
    summary="标记打款",
)
async def mark_expense_paid(
    expense_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """标记报销已打款"""
    site_id = get_site_id(request)
    expense = await expense_service.mark_expense_paid(
        db,
        expense_id=expense_id,
        admin_id=admin.id,
        site_id=site_id,
    )
    await db.commit()
    result = ExpenseRequestResponse.model_validate(expense)
    return ResponseModel.success(data=result, message="已标记打款")
