"""
报表路由

- GET /sales — 销售报表（支持日/周/月粒度）
- GET /users — 用户分析
- GET /products — 商品排行
- POST /export — 报表导出
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from models.order import Order, OrderItem
from models.product import Product
from models.user import User
from schemas.common import ResponseModel

router = APIRouter(prefix="/api/v1/admin/reports", tags=["报表"])


@router.get("/sales", summary="销售报表")
async def get_sales_report(
    request: Request,
    granularity: str = Query("day", regex="^(day|week|month)$"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """销售报表：按日/周/月粒度统计订单数、收入、退款等"""
    site_id = get_site_id(request)
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    # 汇总统计
    summary_result = await db.execute(
        select(
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_income"),
            func.coalesce(func.avg(Order.total_amount), 0).label("avg_order_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (Order.status == "refunded", Order.total_amount),
                        else_=0,
                    )
                ),
                0,
            ).label("refund_amount"),
        ).where(
            Order.created_at >= dt_start,
            Order.created_at <= dt_end,
            Order.status.in_(["paid", "completed", "refunded", "checked_in"]),
            Order.site_id == site_id,
        )
    )
    row = summary_result.one()
    total_orders = row.total_orders or 0
    total_income = float(row.total_income or 0)
    avg_order_amount = float(row.avg_order_amount or 0)
    refund_amount = float(row.refund_amount or 0)

    # 计算环比（上一个同等时段）
    period_days = (dt_end - dt_start).days + 1
    prev_start = dt_start - timedelta(days=period_days)
    prev_end = dt_start - timedelta(seconds=1)

    prev_result = await db.execute(
        select(
            func.coalesce(func.sum(Order.total_amount), 0).label("prev_income"),
        ).where(
            Order.created_at >= prev_start,
            Order.created_at <= prev_end,
            Order.status.in_(["paid", "completed", "refunded", "checked_in"]),
            Order.site_id == site_id,
        )
    )
    prev_income = float(prev_result.scalar() or 0)
    mom_rate = ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0

    # 明细数据 — 根据粒度分组
    if granularity == "day":
        date_trunc = func.date(Order.created_at)
    elif granularity == "week":
        # 按 ISO 周分组
        date_trunc = func.strftime("%Y-W%W", Order.created_at)
    else:  # month
        date_trunc = func.strftime("%Y-%m", Order.created_at)

    details_result = await db.execute(
        select(
            date_trunc.label("period"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (Order.status == "refunded", Order.total_amount),
                        else_=0,
                    )
                ),
                0,
            ).label("refund"),
        )
        .where(
            Order.created_at >= dt_start,
            Order.created_at <= dt_end,
            Order.status.in_(["paid", "completed", "refunded", "checked_in"]),
            Order.site_id == site_id,
        )
        .group_by("period")
        .order_by("period")
    )
    details = []
    for r in details_result.all():
        period_date = str(r.period) if r.period else ""
        orders_count = r.orders or 0
        income_val = float(r.income or 0)
        refund_val = float(r.refund or 0)
        avg_val = income_val / orders_count if orders_count > 0 else 0
        details.append({
            "date": period_date,
            "orders": orders_count,
            "income": int(income_val),
            "refund": int(refund_val),
            "avg_amount": int(avg_val),
        })

    return ResponseModel.success(data={
        "summary": {
            "total_orders": total_orders,
            "total_income": int(total_income),
            "avg_order_amount": int(avg_order_amount),
            "refund_amount": int(refund_amount),
            "mom_rate": round(mom_rate, 2),
            "yoy_rate": 0,  # 同比需要去年数据，暂返回 0
        },
        "details": details,
    })


@router.get("/users", summary="用户分析")
async def get_user_report(
    request: Request,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """用户分析报表：新增用户、活跃用户趋势等"""
    site_id = get_site_id(request)
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")

    # 每日新增用户
    new_users_result = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(
            User.created_at >= dt_start,
            User.created_at <= dt_end,
            User.site_id == site_id,
        )
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    new_users = [{"date": str(r.date), "count": r.count} for r in new_users_result.all()]

    # 每日下单用户数（去重）
    active_users_result = await db.execute(
        select(
            func.date(Order.created_at).label("date"),
            func.count(func.distinct(Order.user_id)).label("count"),
        )
        .where(
            Order.created_at >= dt_start,
            Order.created_at <= dt_end,
            Order.site_id == site_id,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    active_users = [{"date": str(r.date), "count": r.count} for r in active_users_result.all()]

    # 总用户数
    total_result = await db.execute(
        select(func.count(User.id)).where(User.site_id == site_id)
    )
    total_users = total_result.scalar() or 0

    return ResponseModel.success(data={
        "total_users": total_users,
        "new_users": new_users,
        "active_users": active_users,
    })


@router.get("/products", summary="商品排行")
async def get_product_report(
    request: Request,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    sort_by: str = Query("sales", regex="^(sales|revenue)$"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """商品排行报表：按销量或收入排行"""
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")

    order_col = (
        func.sum(OrderItem.quantity).label("total_sales")
        if sort_by == "sales"
        else func.sum(OrderItem.subtotal).label("total_revenue")
    )

    result = await db.execute(
        select(
            Product.id,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity).label("total_sales"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.created_at >= dt_start,
            Order.created_at <= dt_end,
            Order.status.in_(["paid", "completed", "checked_in"]),
            Order.site_id == get_site_id(request),
        )
        .group_by(Product.id)
        .order_by(order_col.desc())
        .limit(20)
    )
    items = []
    for r in result.all():
        items.append({
            "product_id": r.id,
            "product_name": r.name,
            "category": r.category,
            "total_sales": r.total_sales or 0,
            "total_revenue": float(r.total_revenue or 0),
        })

    return ResponseModel.success(data={"items": items})


@router.post("/export", summary="报表导出")
async def export_report(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """报表导出（暂返回提示，后续可对接 Excel 生成）"""
    return ResponseModel.success(message="报表导出功能开发中", data={"status": "pending"})
