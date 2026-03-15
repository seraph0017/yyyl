"""
报销服务

- create_expense_request：提交报销
- approve_expense：审批报销（含自审禁止、>=1000元需super_admin）
- mark_expense_paid：标记打款
- list_expenses：列表查询
- get_expense_stats：报销统计

- create_expense_type / update_expense_type / list_expense_types：报销类型管理
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.admin import AdminUser
from models.expense import ExpenseRequest, ExpenseType

logger = logging.getLogger(__name__)

# 排序字段白名单
ALLOWED_SORT_FIELDS = {"id", "amount", "expense_date", "created_at", "status"}

# 需要 super_admin 审批的金额阈值
HIGH_AMOUNT_THRESHOLD = Decimal("1000.00")


# ---- 报销类型管理 ----

async def create_expense_type(
    db: AsyncSession,
    data: Dict[str, Any],
    site_id: int = 1,
) -> ExpenseType:
    """创建报销类型

    Args:
        db: 数据库会话
        data: 报销类型数据
        site_id: 营地ID

    Returns:
        创建的 ExpenseType 实例
    """
    expense_type = ExpenseType(site_id=site_id, **data)
    db.add(expense_type)
    await db.flush()
    logger.info(f"[报销] 创建类型: id={expense_type.id}, name={expense_type.name}")
    return expense_type


async def update_expense_type(
    db: AsyncSession,
    type_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> ExpenseType:
    """更新报销类型

    Args:
        db: 数据库会话
        type_id: 类型ID
        data: 更新数据
        site_id: 营地ID

    Returns:
        更新后的 ExpenseType 实例
    """
    result = await db.execute(
        select(ExpenseType).where(
            ExpenseType.id == type_id,
            ExpenseType.site_id == site_id,
            ExpenseType.is_deleted.is_(False),
        )
    )
    expense_type = result.scalar_one_or_none()

    if expense_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "报销类型不存在"},
        )

    for key, value in data.items():
        if hasattr(expense_type, key) and value is not None:
            setattr(expense_type, key, value)

    await db.flush()
    logger.info(f"[报销] 更新类型: id={type_id}")
    return expense_type


async def list_expense_types(
    db: AsyncSession,
    site_id: int = 1,
) -> List[ExpenseType]:
    """获取报销类型列表

    Args:
        db: 数据库会话
        site_id: 营地ID

    Returns:
        报销类型列表
    """
    result = await db.execute(
        select(ExpenseType)
        .where(
            ExpenseType.site_id == site_id,
            ExpenseType.is_deleted.is_(False),
        )
        .order_by(ExpenseType.sort_order.asc(), ExpenseType.id.asc())
    )
    return list(result.scalars().all())


# ---- 报销申请 ----

async def create_expense_request(
    db: AsyncSession,
    user_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> ExpenseRequest:
    """提交报销申请

    Args:
        db: 数据库会话
        user_id: 报销人ID（管理员ID）
        data: 报销数据
        site_id: 营地ID

    Returns:
        创建的 ExpenseRequest 实例
    """
    # 校验报销类型存在且有效
    expense_type_id = data.get("expense_type_id")
    type_result = await db.execute(
        select(ExpenseType).where(
            ExpenseType.id == expense_type_id,
            ExpenseType.site_id == site_id,
            ExpenseType.is_deleted.is_(False),
            ExpenseType.status == "active",
        )
    )
    if type_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "报销类型不存在或已停用"},
        )

    expense = ExpenseRequest(
        user_id=user_id,
        site_id=site_id,
        status="pending",
        **data,
    )
    db.add(expense)
    await db.flush()

    logger.info(
        f"[报销] 提交申请: id={expense.id}, user={user_id}, "
        f"amount={expense.amount}"
    )
    return expense


async def approve_expense(
    db: AsyncSession,
    expense_id: int,
    admin_id: int,
    approved: bool,
    review_remark: Optional[str] = None,
    site_id: int = 1,
) -> ExpenseRequest:
    """审批报销

    业务规则：
    1. 不允许自审（reviewer_id != user_id，数据库约束保底）
    2. 金额 >= 1000 元需 super_admin 角色

    Args:
        db: 数据库会话
        expense_id: 报销申请ID
        admin_id: 审批人ID
        approved: 是否通过
        review_remark: 审批备注
        site_id: 营地ID

    Returns:
        更新后的 ExpenseRequest 实例
    """
    result = await db.execute(
        select(ExpenseRequest).where(
            ExpenseRequest.id == expense_id,
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
        )
    )
    expense = result.scalar_one_or_none()

    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "报销申请不存在"},
        )

    if expense.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "报销申请不在待审批状态"},
        )

    # 自审禁止
    if expense.user_id == admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": "不允许审批自己的报销申请"},
        )

    # 高额审批权限检查
    if expense.amount >= HIGH_AMOUNT_THRESHOLD:
        admin_result = await db.execute(
            select(AdminUser)
            .options(selectinload(AdminUser.role))
            .where(AdminUser.id == admin_id)
        )
        admin = admin_result.scalar_one_or_none()

        if admin is None or admin.role is None or admin.role.role_code != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": 40302,
                    "message": f"金额≥{HIGH_AMOUNT_THRESHOLD}元的报销需要超级管理员审批",
                },
            )

    now = datetime.now(timezone.utc)

    if approved:
        expense.status = "approved"
    else:
        expense.status = "rejected"

    expense.reviewer_id = admin_id
    expense.reviewed_at = now
    expense.review_remark = review_remark

    await db.flush()
    logger.info(
        f"[报销] 审批: id={expense_id}, approved={approved}, "
        f"reviewer={admin_id}"
    )
    return expense


async def mark_expense_paid(
    db: AsyncSession,
    expense_id: int,
    admin_id: int,
    site_id: int = 1,
) -> ExpenseRequest:
    """标记报销已打款

    Args:
        db: 数据库会话
        expense_id: 报销申请ID
        admin_id: 打款操作人ID
        site_id: 营地ID

    Returns:
        更新后的 ExpenseRequest 实例
    """
    result = await db.execute(
        select(ExpenseRequest).where(
            ExpenseRequest.id == expense_id,
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
        )
    )
    expense = result.scalar_one_or_none()

    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "报销申请不存在"},
        )

    if expense.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "报销申请不在已审批状态"},
        )

    expense.status = "paid"
    expense.paid_at = datetime.now(timezone.utc)
    expense.paid_by = admin_id

    await db.flush()
    logger.info(f"[报销] 标记打款: id={expense_id}, paid_by={admin_id}")
    return expense


async def list_expenses(
    db: AsyncSession,
    site_id: int = 1,
    page: int = 1,
    page_size: int = 20,
    expense_status: Optional[str] = None,
    expense_type_id: Optional[int] = None,
    user_id: Optional[int] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[ExpenseRequest], int]:
    """报销列表查询

    Args:
        db: 数据库会话
        site_id: 营地ID
        page: 页码
        page_size: 每页数量
        expense_status: 状态筛选
        expense_type_id: 类型筛选
        user_id: 报销人筛选
        date_start: 开始日期
        date_end: 结束日期
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        (报销列表, 总数)
    """
    query = (
        select(ExpenseRequest)
        .where(
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
        )
    )

    if expense_status:
        query = query.where(ExpenseRequest.status == expense_status)
    if expense_type_id:
        query = query.where(ExpenseRequest.expense_type_id == expense_type_id)
    if user_id:
        query = query.where(ExpenseRequest.user_id == user_id)
    if date_start:
        query = query.where(ExpenseRequest.expense_date >= date_start)
    if date_end:
        query = query.where(ExpenseRequest.expense_date <= date_end)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(ExpenseRequest, sort_by)
        query = query.order_by(
            order_col.desc() if sort_order == "desc" else order_col.asc()
        )
    else:
        query = query.order_by(ExpenseRequest.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    expenses = list(result.scalars().all())

    return expenses, total


async def get_expense_stats(
    db: AsyncSession,
    site_id: int = 1,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """报销统计

    Args:
        db: 数据库会话
        site_id: 营地ID
        year: 年份（默认当前年）
        month: 月份（默认当前月）

    Returns:
        报销统计数据
    """
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    # 已通过/已打款的报销（统计有效报销）
    approved_statuses = ("approved", "paid")

    # 总金额（所有时间）
    total_amount_result = await db.execute(
        select(func.coalesce(func.sum(ExpenseRequest.amount), 0)).where(
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
            ExpenseRequest.status.in_(approved_statuses),
        )
    )
    total_amount = total_amount_result.scalar() or Decimal("0")

    # 当月总金额
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    month_total_result = await db.execute(
        select(func.coalesce(func.sum(ExpenseRequest.amount), 0)).where(
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
            ExpenseRequest.status.in_(approved_statuses),
            ExpenseRequest.expense_date >= month_start,
            ExpenseRequest.expense_date < month_end,
        )
    )
    month_total = month_total_result.scalar() or Decimal("0")

    # 按类型统计（当月）
    type_breakdown_result = await db.execute(
        select(
            ExpenseRequest.expense_type_id,
            func.coalesce(func.sum(ExpenseRequest.amount), 0).label("total_amount"),
            func.count().label("count"),
        )
        .where(
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
            ExpenseRequest.status.in_(approved_statuses),
            ExpenseRequest.expense_date >= month_start,
            ExpenseRequest.expense_date < month_end,
        )
        .group_by(ExpenseRequest.expense_type_id)
    )
    type_rows = type_breakdown_result.all()

    # 查询类型名称
    type_breakdown = []
    if type_rows:
        type_ids = [row.expense_type_id for row in type_rows]
        types_result = await db.execute(
            select(ExpenseType.id, ExpenseType.name).where(
                ExpenseType.id.in_(type_ids)
            )
        )
        type_name_map = {r.id: r.name for r in types_result.all()}

        for row in type_rows:
            type_breakdown.append({
                "expense_type_id": row.expense_type_id,
                "expense_type_name": type_name_map.get(row.expense_type_id, ""),
                "total_amount": row.total_amount,
                "count": row.count,
            })

    # 按员工统计（当月）
    staff_breakdown_result = await db.execute(
        select(
            ExpenseRequest.user_id,
            func.coalesce(func.sum(ExpenseRequest.amount), 0).label("total_amount"),
            func.count().label("count"),
        )
        .where(
            ExpenseRequest.site_id == site_id,
            ExpenseRequest.is_deleted.is_(False),
            ExpenseRequest.status.in_(approved_statuses),
            ExpenseRequest.expense_date >= month_start,
            ExpenseRequest.expense_date < month_end,
        )
        .group_by(ExpenseRequest.user_id)
    )
    staff_rows = staff_breakdown_result.all()

    staff_breakdown = []
    if staff_rows:
        staff_ids = [row.user_id for row in staff_rows]
        staffs_result = await db.execute(
            select(AdminUser.id, AdminUser.real_name).where(
                AdminUser.id.in_(staff_ids)
            )
        )
        staff_name_map = {r.id: r.real_name or "" for r in staffs_result.all()}

        for row in staff_rows:
            staff_breakdown.append({
                "user_id": row.user_id,
                "staff_name": staff_name_map.get(row.user_id, ""),
                "total_amount": row.total_amount,
                "count": row.count,
            })

    return {
        "total_amount": total_amount,
        "month_total": month_total,
        "type_breakdown": type_breakdown,
        "staff_breakdown": staff_breakdown,
    }
