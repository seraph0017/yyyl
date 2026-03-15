"""
绩效服务

- get_performance_configs：获取绩效系数配置
- update_performance_configs：更新绩效系数
- calculate_performance：计算绩效
- list_performance_records：绩效记录列表
- get_performance_ranking：绩效排名
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.admin import AdminUser
from models.finance import FinanceTransaction
from models.order import Order, OrderItem
from models.performance import PerformanceConfig, PerformanceDetail, PerformanceRecord

logger = logging.getLogger(__name__)

# 排序字段白名单
ALLOWED_SORT_FIELDS = {
    "id", "period_start", "period_end", "total_income",
    "total_performance", "created_at",
}

# 商品类型到收入类型的映射
PRODUCT_TYPE_TO_INCOME_TYPE = {
    "daily_camping": "campsite",
    "event_camping": "campsite",
    "rental": "rental",
    "shop": "shop",
    "merchandise": "shop",
    "daily_activity": "activity",
    "special_activity": "activity",
    "insurance": "campsite",  # 保险归属到露营
}


async def get_performance_configs(
    db: AsyncSession,
    site_id: int = 1,
) -> List[PerformanceConfig]:
    """获取绩效系数配置

    Args:
        db: 数据库会话
        site_id: 营地ID

    Returns:
        绩效系数配置列表
    """
    result = await db.execute(
        select(PerformanceConfig)
        .where(
            PerformanceConfig.site_id == site_id,
            PerformanceConfig.is_deleted.is_(False),
        )
        .order_by(PerformanceConfig.income_type)
    )
    return list(result.scalars().all())


async def update_performance_configs(
    db: AsyncSession,
    configs: List[Dict[str, Any]],
    site_id: int = 1,
) -> List[PerformanceConfig]:
    """更新绩效系数配置（upsert 语义）

    Args:
        db: 数据库会话
        configs: 绩效系数配置列表
        site_id: 营地ID

    Returns:
        更新后的配置列表
    """
    results = []

    for config_data in configs:
        income_type = config_data["income_type"]
        coefficient = config_data["coefficient"]
        description = config_data.get("description")

        # 查找现有配置
        result = await db.execute(
            select(PerformanceConfig).where(
                PerformanceConfig.income_type == income_type,
                PerformanceConfig.site_id == site_id,
                PerformanceConfig.is_deleted.is_(False),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.coefficient = coefficient
            if description is not None:
                existing.description = description
            results.append(existing)
        else:
            new_config = PerformanceConfig(
                income_type=income_type,
                coefficient=coefficient,
                description=description,
                site_id=site_id,
            )
            db.add(new_config)
            await db.flush()
            results.append(new_config)

    await db.flush()
    logger.info(f"[绩效] 更新配置: count={len(configs)}, site_id={site_id}")
    return results


async def calculate_performance(
    db: AsyncSession,
    site_id: int = 1,
    period_type: str = "daily",
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> List[PerformanceRecord]:
    """计算绩效

    根据绩效系数配置和订单数据，计算每个员工的绩效。
    规则：订单的 assigned_staff_id 为绩效归属员工。

    Args:
        db: 数据库会话
        site_id: 营地ID
        period_type: 周期类型: daily/weekly/monthly
        period_start: 周期开始日期
        period_end: 周期结束日期

    Returns:
        计算后的绩效记录列表
    """
    if period_start is None:
        period_start = date.today()

    # 自动计算周期结束日期
    if period_end is None:
        if period_type == "daily":
            period_end = period_start
        elif period_type == "weekly":
            period_end = period_start + timedelta(days=6)
        elif period_type == "monthly":
            # 取当月最后一天
            if period_start.month == 12:
                period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

    # 获取绩效系数配置
    config_result = await db.execute(
        select(PerformanceConfig).where(
            PerformanceConfig.site_id == site_id,
            PerformanceConfig.is_deleted.is_(False),
        )
    )
    configs = list(config_result.scalars().all())
    coefficient_map = {c.income_type: c.coefficient for c in configs}

    if not coefficient_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40001, "message": "请先配置绩效系数"},
        )

    # 按 assigned_staff_id 聚合订单收入
    # 只统计已支付的有效订单
    staff_income_query = (
        select(
            Order.assigned_staff_id,
            Order.order_type,
            func.coalesce(func.sum(Order.actual_amount), 0).label("income"),
        )
        .where(
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
            Order.assigned_staff_id.isnot(None),
            func.date(Order.payment_time) >= period_start,
            func.date(Order.payment_time) <= period_end,
        )
        .group_by(Order.assigned_staff_id, Order.order_type)
    )

    income_result = await db.execute(staff_income_query)
    income_rows = income_result.all()

    # 按员工聚合
    staff_data: Dict[int, Dict[str, Decimal]] = {}
    for row in income_rows:
        staff_id = row.assigned_staff_id
        order_type = row.order_type
        income = Decimal(str(row.income))
        income_type = PRODUCT_TYPE_TO_INCOME_TYPE.get(order_type, "campsite")

        if staff_id not in staff_data:
            staff_data[staff_id] = {}
        staff_data[staff_id][income_type] = (
            staff_data[staff_id].get(income_type, Decimal("0")) + income
        )

    # 创建绩效记录
    records = []
    for staff_id, incomes in staff_data.items():
        total_income = Decimal("0")
        total_performance = Decimal("0")
        details_data = []

        for income_type, income_amount in incomes.items():
            coeff = coefficient_map.get(income_type, Decimal("0"))
            perf_amount = (income_amount * coeff).quantize(Decimal("0.01"))

            total_income += income_amount
            total_performance += perf_amount

            details_data.append({
                "income_type": income_type,
                "income_amount": income_amount,
                "performance_amount": perf_amount,
            })

        # 检查是否已有记录（防重复计算）
        existing_result = await db.execute(
            select(PerformanceRecord).where(
                PerformanceRecord.staff_user_id == staff_id,
                PerformanceRecord.period_type == period_type,
                PerformanceRecord.period_start == period_start,
                PerformanceRecord.site_id == site_id,
                PerformanceRecord.is_deleted.is_(False),
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            # 更新已有记录
            existing.total_income = total_income
            existing.total_performance = total_performance
            existing.period_end = period_end

            # 删除旧明细，插入新明细
            for detail in existing.details:
                detail.is_deleted = True

            for d in details_data:
                detail = PerformanceDetail(
                    record_id=existing.id,
                    **d,
                )
                db.add(detail)

            records.append(existing)
        else:
            # 创建新记录
            record = PerformanceRecord(
                staff_user_id=staff_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                total_income=total_income,
                total_performance=total_performance,
                site_id=site_id,
            )
            db.add(record)
            await db.flush()

            for d in details_data:
                detail = PerformanceDetail(
                    record_id=record.id,
                    **d,
                )
                db.add(detail)

            records.append(record)

    await db.flush()
    logger.info(
        f"[绩效] 计算完成: period={period_type}, "
        f"start={period_start}, end={period_end}, "
        f"staff_count={len(records)}"
    )
    return records


async def list_performance_records(
    db: AsyncSession,
    site_id: int = 1,
    staff_user_id: Optional[int] = None,
    period_type: Optional[str] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[PerformanceRecord], int]:
    """绩效记录列表

    Args:
        db: 数据库会话
        site_id: 营地ID
        staff_user_id: 员工ID筛选
        period_type: 周期类型筛选
        period_start: 开始日期
        period_end: 结束日期
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        (记录列表, 总数)
    """
    query = (
        select(PerformanceRecord)
        .options(selectinload(PerformanceRecord.details))
        .where(
            PerformanceRecord.site_id == site_id,
            PerformanceRecord.is_deleted.is_(False),
        )
    )

    if staff_user_id:
        query = query.where(PerformanceRecord.staff_user_id == staff_user_id)
    if period_type:
        query = query.where(PerformanceRecord.period_type == period_type)
    if period_start:
        query = query.where(PerformanceRecord.period_start >= period_start)
    if period_end:
        query = query.where(PerformanceRecord.period_end <= period_end)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(PerformanceRecord, sort_by)
        query = query.order_by(
            order_col.desc() if sort_order == "desc" else order_col.asc()
        )
    else:
        query = query.order_by(PerformanceRecord.period_start.desc(), PerformanceRecord.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    records = list(result.scalars().unique().all())

    return records, total


async def get_performance_ranking(
    db: AsyncSession,
    site_id: int = 1,
    period_type: str = "monthly",
    period_start: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """绩效排名

    Args:
        db: 数据库会话
        site_id: 营地ID
        period_type: 周期类型
        period_start: 周期开始日期

    Returns:
        绩效排名列表
    """
    if period_start is None:
        today = date.today()
        period_start = today.replace(day=1)

    query = (
        select(
            PerformanceRecord.staff_user_id,
            func.sum(PerformanceRecord.total_performance).label("total_performance"),
            func.sum(PerformanceRecord.total_income).label("total_income"),
        )
        .where(
            PerformanceRecord.site_id == site_id,
            PerformanceRecord.is_deleted.is_(False),
            PerformanceRecord.period_type == period_type,
            PerformanceRecord.period_start >= period_start,
        )
        .group_by(PerformanceRecord.staff_user_id)
        .order_by(func.sum(PerformanceRecord.total_performance).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return []

    # 查询员工姓名
    staff_ids = [row.staff_user_id for row in rows]
    staff_result = await db.execute(
        select(AdminUser.id, AdminUser.real_name).where(
            AdminUser.id.in_(staff_ids)
        )
    )
    staff_name_map = {r.id: r.real_name or "" for r in staff_result.all()}

    ranking = []
    for idx, row in enumerate(rows, start=1):
        ranking.append({
            "rank": idx,
            "staff_user_id": row.staff_user_id,
            "staff_name": staff_name_map.get(row.staff_user_id, ""),
            "total_performance": row.total_performance,
            "total_income": row.total_income,
        })

    return ranking
