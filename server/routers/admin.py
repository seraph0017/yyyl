"""
管理后台路由

- GET /dashboard/realtime — 实时数据
- GET /dashboard/trends — 趋势图
- GET /dashboard/sales-ranking — 销售排行
- GET /dashboard/member-stats — 会员统计
- GET /dashboard/finance-summary — 财务概览
- GET /dashboard/category-revenue — 品类收入
- GET /dashboard/heatmap — 热力图
- GET /users — 用户列表
- GET /members — 会员管理
- GET /logs — 操作日志
- GET /calendar — 营地日历
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select, and_, case, cast, Date as SADate
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminPermission, AdminRole, AdminUser, OperationLog
from models.content import (
    DisclaimerTemplate, FaqCategory, FaqItem, PageConfig,
)
from models.member import (
    ActivationCode, AnnualCard, AnnualCardConfig,
    PointsExchangeConfig, TimesCard, TimesCardConfig,
)
from models.notification import Notification
from models.order import Order, OrderItem
from models.product import DateTypeConfig, DiscountRule, Inventory, PricingRule, Product
from models.user import User
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

@router.get("/dashboard/realtime", summary="实时数据")
async def get_dashboard_realtime(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取实时数据卡片：今日订单/收入/在营人数/库存告警"""
    site_id = get_site_id(request)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # 今日订单数 + 收入
    today_stats = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.actual_amount), 0),
        ).where(
            and_(
                Order.created_at >= today_start,
                Order.status.notin_(["cancelled", "pending_payment"]),
                Order.site_id == site_id,
            )
        )
    )
    today_orders, today_income = today_stats.one()

    # 昨日订单数 + 收入
    yesterday_stats = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.actual_amount), 0),
        ).where(
            and_(
                Order.created_at >= yesterday_start,
                Order.created_at < today_start,
                Order.status.notin_(["cancelled", "pending_payment"]),
                Order.site_id == site_id,
            )
        )
    )
    yesterday_orders, yesterday_income = yesterday_stats.one()

    # 库存告警：未来3天可用库存 <= 2 的营位天数
    alert_result = await db.execute(
        select(func.count(Inventory.id))
        .join(Product, Product.id == Inventory.product_id)
        .where(
            and_(
                Inventory.date >= now.date(),
                Inventory.date <= now.date() + timedelta(days=3),
                Inventory.available <= 2,
                Inventory.status == "open",
                Product.site_id == site_id,
            )
        )
    )
    stock_alerts = alert_result.scalar() or 0

    # 趋势判断
    orders_trend = "up" if today_orders > yesterday_orders else ("down" if today_orders < yesterday_orders else "flat")
    income_trend = "up" if today_income > yesterday_income else ("down" if today_income < yesterday_income else "flat")

    return ResponseModel.success(data={
        "today_orders": today_orders,
        "today_income": int(today_income * 100),  # 转为分
        "current_visitors": 0,  # 暂无入园数据
        "stock_alerts": stock_alerts,
        "yesterday_orders": yesterday_orders,
        "yesterday_income": int(yesterday_income * 100),
        "orders_trend": orders_trend,
        "income_trend": income_trend,
    })


@router.get("/dashboard/trends", summary="趋势图")
async def get_dashboard_trends(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="天数"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取订单和收入趋势图数据"""
    site_id = get_site_id(request)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    order_date = cast(Order.created_at, SADate)
    result = await db.execute(
        select(
            order_date.label("d"),
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.actual_amount), 0).label("rev"),
        ).where(
            and_(
                Order.created_at >= start,
                Order.status.notin_(["cancelled", "pending_payment"]),
                Order.site_id == site_id,
            )
        ).group_by(order_date).order_by(order_date)
    )
    rows = result.all()

    # 构建完整日期序列
    date_map = {str(r.d): {"orders": r.cnt, "income": int(r.rev * 100)} for r in rows}
    dates = []
    orders = []
    income = []
    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).date()
        ds = str(d)
        label = f"{d.month}/{d.day}"
        dates.append(label)
        data = date_map.get(ds, {"orders": 0, "income": 0})
        orders.append(data["orders"])
        income.append(data["income"])

    return ResponseModel.success(data={
        "dates": dates,
        "orders": orders,
        "income": income,
    })


@router.get("/dashboard/sales-ranking", summary="销售排行")
async def get_sales_ranking(
    request: Request,
    sort_by: str = Query("sales_count", description="排序: sales_count/sales_amount"),
    top: int = Query(10, ge=1, le=50, description="排名数量"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取商品销售排行榜"""
    site_id = get_site_id(request)
    # 按已支付订单统计
    order_col = func.count(OrderItem.id).label("sales_count")
    amount_col = func.coalesce(func.sum(OrderItem.actual_price * OrderItem.quantity), 0).label("sales_amount")

    sort_col = order_col if sort_by == "sales_count" else amount_col

    result = await db.execute(
        select(
            OrderItem.product_id,
            Product.name.label("product_name"),
            Product.type.label("category"),
            order_col,
            amount_col,
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Order.status.notin_(["cancelled", "pending_payment"]), Order.site_id == site_id)
        .group_by(OrderItem.product_id, Product.name, Product.type)
        .order_by(sort_col.desc())
        .limit(top)
    )
    rows = result.all()

    data = []
    for r in rows:
        data.append({
            "product_id": r.product_id,
            "product_name": r.product_name,
            "category": r.category,
            "sales_count": r.sales_count,
            "sales_amount": int(r.sales_amount * 100),
            "cover_image": "",
        })

    return ResponseModel.success(data=data)


@router.get("/dashboard/member-stats", summary="会员统计")
async def get_member_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取会员数据统计"""
    site_id = get_site_id(request)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # 总用户数 + 会员数
    user_stats = await db.execute(
        select(
            func.count(User.id),
            func.count(case((User.is_member == True, User.id))),
        ).where(User.site_id == site_id)
    )
    total_users, total_members = user_stats.one()

    # 年卡会员（有效期内）
    annual_result = await db.execute(
        select(func.count(AnnualCard.id)).where(AnnualCard.status == "active", AnnualCard.site_id == site_id)
    )
    annual_active = annual_result.scalar() or 0

    # 次数卡用户
    times_result = await db.execute(
        select(func.count(TimesCard.id)).where(TimesCard.status == "active", TimesCard.site_id == site_id)
    )
    times_active = times_result.scalar() or 0

    # 活跃会员（30天内有登录）
    # last_login_at 是 naive timestamp，需要用 naive datetime 比较
    thirty_days_ago = (now - timedelta(days=30)).replace(tzinfo=None)
    active_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.is_member == True,
                User.last_login_at >= thirty_days_ago,
                User.site_id == site_id,
            )
        )
    )
    active_members = active_result.scalar() or 0

    # 新增用户
    new_today = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start, User.site_id == site_id)
    )
    new_week = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start, User.site_id == site_id)
    )
    new_month = await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_start, User.site_id == site_id)
    )

    return ResponseModel.success(data={
        "total_members": total_members,
        "annual_members": annual_active,
        "times_card_holders": times_active,
        "active_members": active_members,
        "new_today": new_today.scalar() or 0,
        "new_this_week": new_week.scalar() or 0,
        "new_this_month": new_month.scalar() or 0,
    })


@router.get("/dashboard/finance-summary", summary="财务概览")
async def get_finance_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取财务概览数据"""
    site_id = get_site_id(request)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # 待确认金额（待支付订单）
    pending = await db.execute(
        select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
            Order.status == "pending_payment",
            Order.site_id == site_id,
        )
    )
    pending_amount = pending.scalar() or 0

    # 可提现 = 已完成订单总额
    withdrawable = await db.execute(
        select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
            Order.status.in_(["completed", "verified"]),
            Order.site_id == site_id,
        )
    )
    withdrawable_amount = withdrawable.scalar() or 0

    # 押金
    deposit = await db.execute(
        select(func.coalesce(func.sum(Order.deposit_amount), 0)).where(
            Order.status.in_(["paid", "verified", "completed"]),
            Order.deposit_amount > 0,
            Order.site_id == site_id,
        )
    )
    deposit_amount = deposit.scalar() or 0

    # 本月收入
    month_income_r = await db.execute(
        select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
            and_(
                Order.created_at >= month_start,
                Order.status.notin_(["cancelled", "pending_payment"]),
                Order.site_id == site_id,
            )
        )
    )
    month_income = month_income_r.scalar() or 0

    # 上月收入
    last_month_income_r = await db.execute(
        select(func.coalesce(func.sum(Order.actual_amount), 0)).where(
            and_(
                Order.created_at >= last_month_start,
                Order.created_at < month_start,
                Order.status.notin_(["cancelled", "pending_payment"]),
                Order.site_id == site_id,
            )
        )
    )
    last_month_income = last_month_income_r.scalar() or 0

    # 环比
    mom_rate = 0.0
    if last_month_income and last_month_income > 0:
        mom_rate = round(float((month_income - last_month_income) / last_month_income * 100), 1)

    return ResponseModel.success(data={
        "pending_amount": int(pending_amount * 100),
        "withdrawable_amount": int(withdrawable_amount * 100),
        "deposit_amount": int(deposit_amount * 100),
        "month_income": int(month_income * 100),
        "last_month_income": int(last_month_income * 100),
        "mom_rate": mom_rate,
        "yoy_rate": 0,
    })


@router.get("/dashboard/category-revenue", summary="品类收入占比")
async def get_category_revenue(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取品类收入占比"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(
            Order.order_type,
            func.coalesce(func.sum(Order.actual_amount), 0).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .where(Order.status.notin_(["cancelled", "pending_payment"]), Order.site_id == site_id)
        .group_by(Order.order_type)
        .order_by(func.sum(Order.actual_amount).desc())
    )
    rows = result.all()

    total_revenue = sum(float(r.revenue) for r in rows) if rows else 0

    CATEGORY_NAMES = {
        "daily_camping": "日常营位",
        "event_camping": "活动营位",
        "rental": "装备租赁",
        "daily_activity": "日常活动",
        "special_activity": "特定活动",
        "shop": "小商店",
        "merchandise": "周边商品",
        "annual_card": "年卡",
    }

    data = []
    for r in rows:
        pct = round(float(r.revenue) / total_revenue * 100, 1) if total_revenue > 0 else 0
        data.append({
            "category": r.order_type,
            "category_name": CATEGORY_NAMES.get(r.order_type, r.order_type),
            "revenue": int(r.revenue * 100),
            "percentage": pct,
            "order_count": r.order_count,
        })

    return ResponseModel.success(data=data)


@router.get("/dashboard/heatmap", summary="营位预定热力图")
async def get_heatmap(
    request: Request,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取营位预定热力图数据（日期×营位矩阵）"""
    site_id = get_site_id(request)
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=14)

    result = await db.execute(
        select(
            Inventory.product_id,
            Product.name.label("product_name"),
            Inventory.date.label("report_date"),
            Inventory.total,
            Inventory.sold,
        )
        .join(Product, Product.id == Inventory.product_id)
        .where(
            and_(
                Inventory.date >= start_date,
                Inventory.date <= end_date,
                Product.type.in_(["daily_camping", "event_camping"]),
                Product.site_id == site_id,
            )
        )
        .order_by(Inventory.product_id, Inventory.date)
    )
    rows = result.all()

    data = []
    for r in rows:
        occupancy = round(r.sold / r.total * 100, 1) if r.total > 0 else 0
        data.append({
            "product_id": r.product_id,
            "product_name": r.product_name,
            "report_date": str(r.report_date),
            "total": r.total,
            "sold": r.sold,
            "occupancy_rate": occupancy,
        })

    return ResponseModel.success(data=data)


# ========== 用户管理 ==========

@router.get("/users", summary="用户列表")
async def list_users(
    request: Request,
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="用户状态"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端用户列表"""
    site_id = get_site_id(request)
    # 基础查询条件：排除软删除 + site_id 过滤
    conditions = [User.is_deleted == False, User.site_id == site_id]

    # keyword 搜索：匹配 nickname 或 phone
    if keyword:
        like_pattern = f"%{keyword}%"
        conditions.append(
            or_(
                User.nickname.ilike(like_pattern),
                User.phone.ilike(like_pattern),
            )
        )

    # status 筛选
    if status:
        conditions.append(User.status == status)

    # 查询总数
    count_result = await db.execute(
        select(func.count(User.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(
        select(User)
        .where(and_(*conditions))
        .order_by(User.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    users = result.scalars().all()

    items = []
    for u in users:
        items.append({
            "id": u.id,
            "openid": u.openid,
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
            "phone": u.phone,
            "role": u.role,
            "is_member": u.is_member,
            "member_level": u.member_level,
            "points_balance": u.points_balance,
            "status": u.status,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 会员管理 ==========

@router.get("/members", summary="会员管理")
async def list_members(
    request: Request,
    member_level: Optional[str] = Query(None, description="会员等级"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端会员列表"""
    site_id = get_site_id(request)
    # 基础条件：会员 + 未软删除 + site_id 过滤
    conditions = [User.is_member == True, User.is_deleted == False, User.site_id == site_id]

    # 按会员类型筛选：通过子查询判断是否持有相应卡
    if member_level == "annual_card":
        # 有有效年卡的用户
        conditions.append(User.id.in_(
            select(AnnualCard.user_id).where(AnnualCard.status == "active")
        ))
    elif member_level == "times_card":
        # 有有效次数卡的用户
        conditions.append(User.id.in_(
            select(TimesCard.user_id).where(TimesCard.status == "active")
        ))

    # 查询总数
    count_result = await db.execute(
        select(func.count(User.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    # 分页查询用户
    result = await db.execute(
        select(User)
        .where(and_(*conditions))
        .order_by(User.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    users = result.scalars().all()

    # 批量查询年卡和次数卡信息
    user_ids = [u.id for u in users]
    annual_cards_map: dict = {}
    times_cards_map: dict = {}

    if user_ids:
        # 年卡：每个用户的有效年卡
        ac_result = await db.execute(
            select(AnnualCard).where(
                and_(
                    AnnualCard.user_id.in_(user_ids),
                    AnnualCard.status == "active",
                )
            )
        )
        for ac in ac_result.scalars().all():
            annual_cards_map.setdefault(ac.user_id, []).append({
                "id": ac.id,
                "start_date": str(ac.start_date),
                "end_date": str(ac.end_date),
                "status": ac.status,
            })

        # 次数卡：每个用户的有效次数卡
        tc_result = await db.execute(
            select(TimesCard).where(
                and_(
                    TimesCard.user_id.in_(user_ids),
                    TimesCard.status == "active",
                )
            )
        )
        for tc in tc_result.scalars().all():
            times_cards_map.setdefault(tc.user_id, []).append({
                "id": tc.id,
                "total_times": tc.total_times,
                "remaining_times": tc.remaining_times,
                "start_date": str(tc.start_date),
                "end_date": str(tc.end_date),
                "status": tc.status,
            })

    items = []
    for u in users:
        user_annual = annual_cards_map.get(u.id, [])
        user_times = times_cards_map.get(u.id, [])
        items.append({
            "id": u.id,
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
            "phone": u.phone,
            "member_level": u.member_level,
            "points_balance": u.points_balance,
            "status": u.status,
            "has_annual_card": len(user_annual) > 0,
            "annual_cards": user_annual,
            "times_cards_count": len(user_times),
            "times_cards": user_times,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 操作日志 ==========

@router.get("/logs", summary="操作日志")
async def list_operation_logs(
    request: Request,
    params: OperationLogListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """查询管理后台操作日志"""
    site_id = get_site_id(request)
    conditions = [OperationLog.is_deleted == False, OperationLog.site_id == site_id]

    if params.operator_id is not None:
        conditions.append(OperationLog.operator_id == params.operator_id)
    if params.action:
        conditions.append(OperationLog.action == params.action)
    if params.target_type:
        conditions.append(OperationLog.target_type == params.target_type)
    if params.is_high_risk is not None:
        conditions.append(OperationLog.is_high_risk == params.is_high_risk)
    if params.date_start:
        conditions.append(OperationLog.created_at >= datetime.combine(params.date_start, datetime.min.time()))
    if params.date_end:
        # date_end 包含当天，取次日零点
        conditions.append(OperationLog.created_at < datetime.combine(params.date_end + timedelta(days=1), datetime.min.time()))

    # 查询总数
    count_result = await db.execute(
        select(func.count(OperationLog.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(
        select(OperationLog)
        .where(and_(*conditions))
        .order_by(OperationLog.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    logs = result.scalars().all()

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "operator_id": log.operator_id,
            "operator_name": log.operator_name,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "is_high_risk": log.is_high_risk,
            "confirm_result": log.confirm_result,
            "site_id": log.site_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ========== 营地日历 ==========

@router.get("/calendar", summary="营地日历")
async def get_camp_calendar(
    request: Request,
    date_start: date = Query(..., description="开始日期"),
    date_end: date = Query(..., description="结束日期"),
    product_ids: Optional[str] = Query(None, description="商品ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取营地日历数据：库存+价格+预定矩阵"""
    site_id = get_site_id(request)
    # 解析 product_ids（逗号分隔字符串 -> int 列表）
    pid_list: Optional[List[int]] = None
    if product_ids:
        try:
            pid_list = [int(x.strip()) for x in product_ids.split(",") if x.strip()]
        except ValueError:
            pid_list = []

    # 查询库存数据，关联商品名称
    inv_conditions = [
        Inventory.is_deleted == False,
        Inventory.date >= date_start,
        Inventory.date <= date_end,
        Product.site_id == site_id,
    ]
    if pid_list:
        inv_conditions.append(Inventory.product_id.in_(pid_list))

    result = await db.execute(
        select(
            Inventory.id,
            Inventory.product_id,
            Product.name.label("product_name"),
            Product.type.label("product_type"),
            Product.base_price,
            Inventory.date,
            Inventory.total,
            Inventory.available,
            Inventory.sold,
            Inventory.locked,
            Inventory.status,
        )
        .join(Product, Product.id == Inventory.product_id)
        .where(and_(*inv_conditions))
        .order_by(Inventory.product_id, Inventory.date)
    )
    inv_rows = result.all()

    # 收集涉及的 product_id 列表
    involved_product_ids = list({r.product_id for r in inv_rows})

    # 批量查询定价规则（custom_date 和 date_type 两种）
    pricing_map: dict = {}  # {(product_id, date): price}
    dt_price_map: dict = {}  # {product_id: {date_type: price}}
    date_type_map: dict = {}  # {date: date_type}
    if involved_product_ids:
        # 1. custom_date 精确匹配（优先级最高）
        custom_pricing = await db.execute(
            select(PricingRule.product_id, PricingRule.custom_date, PricingRule.price).where(
                and_(
                    PricingRule.product_id.in_(involved_product_ids),
                    PricingRule.rule_type == "custom_date",
                    PricingRule.custom_date >= date_start,
                    PricingRule.custom_date <= date_end,
                    PricingRule.is_deleted == False,
                )
            )
        )
        for pr in custom_pricing.all():
            pricing_map[(pr.product_id, pr.custom_date)] = float(pr.price)

        # 2. date_type 规则（weekday/weekend/holiday）
        dt_pricing_result = await db.execute(
            select(PricingRule.product_id, PricingRule.date_type, PricingRule.price).where(
                and_(
                    PricingRule.product_id.in_(involved_product_ids),
                    PricingRule.rule_type == "date_type",
                    PricingRule.is_deleted == False,
                )
            )
        )
        dt_pricing_rows = dt_pricing_result.all()
        for pr in dt_pricing_rows:
            dt_price_map.setdefault(pr.product_id, {})[pr.date_type] = float(pr.price)

        # 3. 查询日期类型配置（DateTypeConfig）
        date_type_result = await db.execute(
            select(DateTypeConfig.date, DateTypeConfig.date_type).where(
                and_(
                    DateTypeConfig.date >= date_start,
                    DateTypeConfig.date <= date_end,
                )
            )
        )
        for dtc in date_type_result.all():
            date_type_map[dtc.date] = dtc.date_type

    # 构建 products 信息
    products_info: dict = {}
    for r in inv_rows:
        if r.product_id not in products_info:
            products_info[r.product_id] = {
                "id": r.product_id,
                "name": r.product_name,
                "type": r.product_type,
            }

    # 构建 cells
    cells = []
    for r in inv_rows:
        inv_date = r.date

        # 确定价格（4级优先级链）：
        # 1. custom_date 精确匹配
        # 2. DateTypeConfig 配置 + date_type 定价
        # 3. 按星期自动判断 weekday/weekend + date_type 定价
        # 4. 商品 base_price 兜底
        price = None

        # 级别1：custom_date
        price = pricing_map.get((r.product_id, inv_date))

        # 级别2+3：date_type 定价
        if price is None and r.product_id in dt_price_map:
            product_dt_prices = dt_price_map[r.product_id]
            # 先看 DateTypeConfig 配置的日期类型
            configured_dt = date_type_map.get(inv_date)
            if configured_dt and configured_dt in product_dt_prices:
                price = product_dt_prices[configured_dt]
            else:
                # 按星期自动判断
                auto_dt = "weekend" if inv_date.weekday() >= 5 else "weekday"
                price = product_dt_prices.get(auto_dt)

        # 级别4：base_price 兜底
        if price is None:
            price = float(r.base_price)

        # 确定日期类型标签
        dt_label = date_type_map.get(inv_date)
        if not dt_label:
            dt_label = "weekend" if inv_date.weekday() >= 5 else "weekday"

        cells.append({
            "product_id": r.product_id,
            "date": str(inv_date),
            "date_type": dt_label,
            "total": r.total,
            "available": r.available,
            "sold": r.sold,
            "locked": r.locked,
            "price": price,
            "status": r.status,
        })

    return ResponseModel.success(data={
        "date_start": str(date_start),
        "date_end": str(date_end),
        "products": list(products_info.values()),
        "cells": cells,
    })


# ========== 年卡配置管理 ==========

@router.get("/annual-card-configs", summary="年卡配置列表")
async def get_annual_card_configs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取所有年卡配置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(AnnualCardConfig)
        .where(AnnualCardConfig.is_deleted.is_(False), AnnualCardConfig.site_id == site_id)
        .order_by(AnnualCardConfig.id.desc())
    )
    configs = result.scalars().all()

    items = []
    for c in configs:
        items.append({
            "id": c.id,
            "name": c.card_name,
            "price": float(c.price),
            "duration_days": c.duration_days,
            "daily_limit": c.daily_limit_quantity,
            "max_consecutive_days": c.max_consecutive_days,
            "gap_days": c.gap_days,
            "refund_days": c.refund_days,
            "status": c.status,
            "site_id": c.site_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return ResponseModel.success(data=items)


@router.post("/annual-card-configs", summary="创建年卡配置")
async def create_annual_card_config(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建年卡配置"""
    site_id = get_site_id(request)
    config = AnnualCardConfig(
        card_name=body.get("name", ""),
        price=Decimal(str(body.get("price", 0))),
        duration_days=body.get("duration_days", 365),
        daily_limit_quantity=body.get("daily_limit", 1),
        daily_limit_position=body.get("daily_limit_position", 1),
        max_consecutive_days=body.get("max_consecutive_days", 3),
        gap_days=body.get("gap_days", 1),
        refund_days=body.get("refund_days", 7),
        status=body.get("status", "active"),
        site_id=site_id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return ResponseModel.success(data={"id": config.id}, message="年卡配置创建成功")


@router.put("/annual-card-configs/{config_id}", summary="更新年卡配置")
async def update_annual_card_config(
    config_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新年卡配置"""
    result = await db.execute(
        select(AnnualCardConfig).where(
            AnnualCardConfig.id == config_id,
            AnnualCardConfig.is_deleted.is_(False),
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="年卡配置不存在")

    if "name" in body:
        config.card_name = body["name"]
    if "price" in body:
        config.price = Decimal(str(body["price"]))
    if "duration_days" in body:
        config.duration_days = body["duration_days"]
    if "daily_limit" in body:
        config.daily_limit_quantity = body["daily_limit"]
    if "daily_limit_position" in body:
        config.daily_limit_position = body["daily_limit_position"]
    if "max_consecutive_days" in body:
        config.max_consecutive_days = body["max_consecutive_days"]
    if "gap_days" in body:
        config.gap_days = body["gap_days"]
    if "refund_days" in body:
        config.refund_days = body["refund_days"]
    if "status" in body:
        config.status = body["status"]

    await db.commit()
    return ResponseModel.success(message="年卡配置更新成功")


# ========== 积分兑换配置管理 ==========

@router.get("/points-exchange-configs", summary="积分兑换配置列表")
async def get_points_exchange_configs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取所有积分兑换配置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PointsExchangeConfig)
        .where(PointsExchangeConfig.is_deleted.is_(False), PointsExchangeConfig.site_id == site_id)
        .order_by(PointsExchangeConfig.id.desc())
    )
    configs = result.scalars().all()

    items = []
    for c in configs:
        items.append({
            "id": c.id,
            "name": c.name,
            "exchange_type": c.exchange_type,
            "product_id": c.product_id,
            "required_points": c.points_required,
            "stock": c.stock,
            "exchanged_count": c.stock_used,
            "status": c.status,
            "start_date": c.start_at.isoformat() if c.start_at else None,
            "end_date": c.end_at.isoformat() if c.end_at else None,
            "site_id": c.site_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return ResponseModel.success(data=items)


@router.post("/points-exchange-configs", summary="创建积分兑换配置")
async def create_points_exchange_config(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建积分兑换配置"""
    site_id = get_site_id(request)
    config = PointsExchangeConfig(
        name=body.get("name", ""),
        exchange_type=body.get("exchange_type", "product"),
        product_id=body.get("product_id"),
        points_required=body.get("required_points", 100),
        stock=body.get("stock", 0),
        stock_used=0,
        start_at=datetime.fromisoformat(body["start_date"]) if body.get("start_date") else datetime.now(timezone.utc),
        end_at=datetime.fromisoformat(body["end_date"]) if body.get("end_date") else datetime.now(timezone.utc) + timedelta(days=365),
        status=body.get("status", "active"),
        site_id=site_id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return ResponseModel.success(data={"id": config.id}, message="积分兑换配置创建成功")


@router.put("/points-exchange-configs/{config_id}", summary="更新积分兑换配置")
async def update_points_exchange_config(
    config_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新积分兑换配置"""
    result = await db.execute(
        select(PointsExchangeConfig).where(
            PointsExchangeConfig.id == config_id,
            PointsExchangeConfig.is_deleted.is_(False),
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="积分兑换配置不存在")

    if "name" in body:
        config.name = body["name"]
    if "exchange_type" in body:
        config.exchange_type = body["exchange_type"]
    if "product_id" in body:
        config.product_id = body["product_id"]
    if "required_points" in body:
        config.points_required = body["required_points"]
    if "stock" in body:
        config.stock = body["stock"]
    if "status" in body:
        config.status = body["status"]
    if "start_date" in body:
        config.start_at = datetime.fromisoformat(body["start_date"]) if body["start_date"] else None
    if "end_date" in body:
        config.end_at = datetime.fromisoformat(body["end_date"]) if body["end_date"] else None

    await db.commit()
    return ResponseModel.success(message="积分兑换配置更新成功")


# ========== 次数卡配置管理 ==========

@router.get("/times-card-configs", summary="次数卡配置列表")
async def get_times_card_configs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取所有次数卡配置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(TimesCardConfig)
        .where(TimesCardConfig.is_deleted.is_(False), TimesCardConfig.site_id == site_id)
        .order_by(TimesCardConfig.id.desc())
    )
    configs = result.scalars().all()

    items = []
    for c in configs:
        items.append({
            "id": c.id,
            "name": c.card_name,
            "total_times": c.total_times,
            "validity_days": c.validity_days,
            "applicable_products": c.applicable_products,
            "daily_limit": c.daily_limit,
            "status": c.status,
            "site_id": c.site_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return ResponseModel.success(data=items)


@router.post("/times-card-configs", summary="创建次数卡配置")
async def create_times_card_config(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建次数卡配置"""
    site_id = get_site_id(request)
    config = TimesCardConfig(
        card_name=body.get("name", ""),
        total_times=body.get("total_times", 10),
        validity_days=body.get("validity_days", 365),
        applicable_products=body.get("applicable_products", []),
        daily_limit=body.get("daily_limit"),
        status=body.get("status", "active"),
        site_id=site_id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return ResponseModel.success(data={"id": config.id}, message="次数卡配置创建成功")


@router.put("/times-card-configs/{config_id}", summary="更新次数卡配置")
async def update_times_card_config(
    config_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新次数卡配置"""
    result = await db.execute(
        select(TimesCardConfig).where(
            TimesCardConfig.id == config_id,
            TimesCardConfig.is_deleted.is_(False),
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="次数卡配置不存在")

    if "name" in body:
        config.card_name = body["name"]
    if "total_times" in body:
        config.total_times = body["total_times"]
    if "validity_days" in body:
        config.validity_days = body["validity_days"]
    if "applicable_products" in body:
        config.applicable_products = body["applicable_products"]
    if "daily_limit" in body:
        config.daily_limit = body["daily_limit"]
    if "status" in body:
        config.status = body["status"]

    await db.commit()
    return ResponseModel.success(message="次数卡配置更新成功")


# ========== 激活码管理 ==========

@router.get("/activation-codes", summary="激活码列表")
async def get_activation_codes(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    batch_no: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取激活码列表（分页）"""
    site_id = get_site_id(request)
    conditions = [ActivationCode.is_deleted.is_(False), ActivationCode.site_id == site_id]
    if batch_no:
        conditions.append(ActivationCode.batch_no == batch_no)
    if status:
        conditions.append(ActivationCode.status == status)

    # 总数
    count_result = await db.execute(
        select(func.count(ActivationCode.id)).where(*conditions)
    )
    total = count_result.scalar() or 0

    # 查询激活码，关联配置名称
    result = await db.execute(
        select(
            ActivationCode,
            TimesCardConfig.card_name.label("config_name"),
        )
        .join(TimesCardConfig, TimesCardConfig.id == ActivationCode.config_id, isouter=True)
        .where(*conditions)
        .order_by(ActivationCode.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    items = []
    for row in rows:
        code = row[0]
        config_name = row[1] or ""
        items.append({
            "id": code.id,
            "code": code.code,
            "batch_no": code.batch_no,
            "config_id": code.config_id,
            "config_name": config_name,
            "status": code.status,
            "used_by": code.used_by,
            "used_at": code.used_at.isoformat() if code.used_at else None,
            "created_at": code.created_at.isoformat() if code.created_at else None,
        })

    return ResponseModel.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.post("/activation-codes/generate", summary="批量生成激活码")
async def generate_activation_codes(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """批量生成激活码"""
    import secrets
    import string

    site_id = get_site_id(request)

    config_id = body.get("config_id")
    count = body.get("count", 10)
    batch_no = body.get("batch_no") or datetime.now(timezone.utc).strftime("BATCH%Y%m%d%H%M%S")

    if not config_id:
        raise HTTPException(status_code=400, detail="请指定关联配置 config_id")

    if count < 1 or count > 1000:
        raise HTTPException(status_code=400, detail="生成数量须在 1~1000 之间")

    # 验证配置存在
    config_result = await db.execute(
        select(TimesCardConfig).where(
            TimesCardConfig.id == config_id,
            TimesCardConfig.is_deleted.is_(False),
        )
    )
    if not config_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="次数卡配置不存在")

    # 生成激活码
    alphabet = string.ascii_uppercase + string.digits
    codes_created = []
    for _ in range(count):
        code_str = "".join(secrets.choice(alphabet) for _ in range(16))
        code = ActivationCode(
            code=code_str,
            config_id=config_id,
            batch_no=batch_no,
            status="unused",
            site_id=site_id,
        )
        db.add(code)
        codes_created.append(code_str)

    await db.commit()

    return ResponseModel.success(
        data={"batch_no": batch_no, "count": len(codes_created)},
        message=f"成功生成 {len(codes_created)} 个激活码",
    )


# ========== 员工管理 ==========

@router.get("/staff", summary="员工列表")
async def list_staff(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取员工列表"""
    count_result = await db.execute(
        select(func.count(AdminUser.id)).where(AdminUser.is_deleted.is_(False))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(AdminUser)
        .where(AdminUser.is_deleted.is_(False))
        .order_by(AdminUser.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    items = []
    for u in users:
        items.append({
            "id": u.id,
            "username": u.username,
            "phone": u.phone,
            "real_name": u.real_name,
            "role_id": u.role_id,
            "role_name": u.role.role_name if u.role else None,
            "status": u.status,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.post("/staff", summary="创建员工")
async def create_staff(
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建员工账号"""
    import hashlib

    password = body.get("password", "123456")
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    staff = AdminUser(
        username=body.get("phone", ""),
        phone=body.get("phone", ""),
        real_name=body.get("real_name", ""),
        role_id=body.get("role_id"),
        password_hash=password_hash,
        status="active",
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return ResponseModel.success(data={"id": staff.id}, message="员工创建成功")


@router.put("/staff/{staff_id}", summary="更新员工")
async def update_staff(
    staff_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新员工信息"""
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == staff_id, AdminUser.is_deleted.is_(False))
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    if "real_name" in body:
        staff.real_name = body["real_name"]
    if "phone" in body:
        staff.phone = body["phone"]
    if "role_id" in body:
        staff.role_id = body["role_id"]
    if "status" in body:
        staff.status = body["status"]
    await db.commit()
    return ResponseModel.success(message="员工更新成功")


@router.delete("/staff/{staff_id}", summary="删除员工")
async def delete_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除员工（软删除）"""
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == staff_id, AdminUser.is_deleted.is_(False))
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    staff.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="员工已删除")


# ========== 角色与权限 ==========

@router.get("/roles", summary="角色列表")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取角色列表"""
    result = await db.execute(
        select(AdminRole).where(AdminRole.is_deleted.is_(False)).order_by(AdminRole.id)
    )
    roles = result.scalars().all()
    items = []
    for r in roles:
        items.append({
            "id": r.id,
            "role_name": r.role_name,
            "role_code": r.role_code,
            "description": r.description,
            "permission_count": len(r.permissions) if r.permissions else 0,
        })
    return ResponseModel.success(data=items)


@router.get("/roles/{role_id}/permissions", summary="角色权限")
async def get_role_permissions(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取指定角色的权限列表"""
    result = await db.execute(
        select(AdminPermission).where(
            AdminPermission.role_id == role_id,
            AdminPermission.is_deleted.is_(False),
        )
    )
    perms = result.scalars().all()
    items = [{"id": p.id, "resource": p.resource, "action": p.action} for p in perms]
    return ResponseModel.success(data=items)


@router.put("/roles/{role_id}/permissions", summary="更新角色权限")
async def update_role_permissions(
    role_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新角色权限"""
    # 删除旧权限
    old_perms = await db.execute(
        select(AdminPermission).where(AdminPermission.role_id == role_id)
    )
    for p in old_perms.scalars().all():
        await db.delete(p)

    # 添加新权限
    permission_ids = body.get("permission_ids", [])
    for pid in permission_ids:
        perm = AdminPermission(role_id=role_id, resource=str(pid), action="read")
        db.add(perm)

    await db.commit()
    return ResponseModel.success(message="权限更新成功")


# ========== 操作日志（兼容前端 /operation-logs 路径） ==========

@router.get("/operation-logs", summary="操作日志列表")
async def list_operation_logs_compat(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    operator_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """操作日志列表（兼容 operation-logs 路径）"""
    site_id = get_site_id(request)
    conditions = [OperationLog.is_deleted.is_(False), OperationLog.site_id == site_id]
    if operator_id:
        conditions.append(OperationLog.operator_id == operator_id)
    if action:
        conditions.append(OperationLog.action == action)
    if target_type:
        conditions.append(OperationLog.target_type == target_type)
    if start_date:
        conditions.append(OperationLog.created_at >= datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc))
    if end_date:
        conditions.append(OperationLog.created_at <= datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc))

    count_result = await db.execute(select(func.count(OperationLog.id)).where(*conditions))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(OperationLog)
        .where(*conditions)
        .order_by(OperationLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = result.scalars().all()
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "operator_id": log.operator_id,
            "operator_name": log.operator_name,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "is_high_risk": log.is_high_risk,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/operation-logs/{log_id}", summary="操作日志详情")
async def get_operation_log_detail(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """操作日志详情"""
    result = await db.execute(
        select(OperationLog).where(OperationLog.id == log_id, OperationLog.is_deleted.is_(False))
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="操作日志不存在")
    return ResponseModel.success(data={
        "id": log.id,
        "operator_id": log.operator_id,
        "operator_name": log.operator_name,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "is_high_risk": log.is_high_risk,
        "confirm_result": log.confirm_result,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    })


# ========== FAQ管理（管理端CRUD） ==========

@router.get("/faq/categories", summary="FAQ分类列表(管理端)")
async def admin_list_faq_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端获取FAQ分类列表"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(FaqCategory).where(FaqCategory.is_deleted.is_(False), FaqCategory.site_id == site_id).order_by(FaqCategory.sort_order)
    )
    categories = result.scalars().all()
    items = []
    for c in categories:
        items.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "sort_order": c.sort_order,
            "item_count": len([i for i in (c.items or []) if not i.is_deleted]),
        })
    return ResponseModel.success(data=items)


@router.post("/faq/categories", summary="创建FAQ分类")
async def create_faq_category(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建FAQ分类"""
    site_id = get_site_id(request)
    cat = FaqCategory(
        name=body.get("name", ""),
        code=body.get("code", ""),
        sort_order=body.get("sort_order", 0),
        site_id=site_id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return ResponseModel.success(data={"id": cat.id}, message="FAQ分类创建成功")


@router.put("/faq/categories/{category_id}", summary="更新FAQ分类")
async def update_faq_category(
    category_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新FAQ分类"""
    result = await db.execute(
        select(FaqCategory).where(FaqCategory.id == category_id, FaqCategory.is_deleted.is_(False))
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="FAQ分类不存在")
    if "name" in body:
        cat.name = body["name"]
    if "code" in body:
        cat.code = body["code"]
    if "sort_order" in body:
        cat.sort_order = body["sort_order"]
    await db.commit()
    return ResponseModel.success(message="FAQ分类更新成功")


@router.delete("/faq/categories/{category_id}", summary="删除FAQ分类")
async def delete_faq_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除FAQ分类（软删除）"""
    result = await db.execute(
        select(FaqCategory).where(FaqCategory.id == category_id, FaqCategory.is_deleted.is_(False))
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="FAQ分类不存在")
    cat.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="FAQ分类已删除")


@router.get("/faq/items", summary="FAQ条目列表(管理端)")
async def admin_list_faq_items(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端获取FAQ条目列表（分页）"""
    site_id = get_site_id(request)
    conditions = [FaqItem.is_deleted.is_(False), FaqItem.site_id == site_id]
    if category_id:
        conditions.append(FaqItem.category_id == category_id)

    count_result = await db.execute(select(func.count(FaqItem.id)).where(*conditions))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(FaqItem)
        .where(*conditions)
        .order_by(FaqItem.sort_order, FaqItem.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    faq_items = result.scalars().all()
    items = []
    for item in faq_items:
        items.append({
            "id": item.id,
            "category_id": item.category_id,
            "question": item.question,
            "answer": item.answer,
            "keywords": item.keywords,
            "sort_order": item.sort_order,
            "click_count": item.click_count,
            "status": item.status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.post("/faq/items", summary="创建FAQ条目")
async def create_faq_item(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建FAQ条目"""
    site_id = get_site_id(request)
    item = FaqItem(
        category_id=body.get("category_id"),
        question=body.get("question", ""),
        answer=body.get("answer", ""),
        keywords=body.get("keywords", []),
        sort_order=body.get("sort_order", 0),
        status=body.get("status", "active"),
        site_id=site_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ResponseModel.success(data={"id": item.id}, message="FAQ条目创建成功")


@router.put("/faq/items/{item_id}", summary="更新FAQ条目")
async def update_faq_item(
    item_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新FAQ条目"""
    result = await db.execute(
        select(FaqItem).where(FaqItem.id == item_id, FaqItem.is_deleted.is_(False))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ条目不存在")
    if "question" in body:
        item.question = body["question"]
    if "answer" in body:
        item.answer = body["answer"]
    if "keywords" in body:
        item.keywords = body["keywords"]
    if "category_id" in body:
        item.category_id = body["category_id"]
    if "sort_order" in body:
        item.sort_order = body["sort_order"]
    if "status" in body:
        item.status = body["status"]
    await db.commit()
    return ResponseModel.success(message="FAQ条目更新成功")


@router.delete("/faq/items/{item_id}", summary="删除FAQ条目")
async def delete_faq_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除FAQ条目（软删除）"""
    result = await db.execute(
        select(FaqItem).where(FaqItem.id == item_id, FaqItem.is_deleted.is_(False))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ条目不存在")
    item.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="FAQ条目已删除")


# ========== 客服配置 ==========

@router.put("/customer-service/config", summary="更新客服配置")
async def update_customer_service_config(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新客服配置（存储在 page_config 表中）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(PageConfig.page_key == "customer_service", PageConfig.site_id == site_id)
    )
    config = result.scalar_one_or_none()
    if config:
        config.config_data = body
    else:
        config = PageConfig(page_key="customer_service", config_data=body, status="active", site_id=site_id)
        db.add(config)
    await db.commit()
    return ResponseModel.success(message="客服配置更新成功")


# ========== 页面配置管理 ==========

@router.get("/page-configs", summary="页面配置列表")
async def list_page_configs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取所有页面配置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(PageConfig.is_deleted.is_(False), PageConfig.site_id == site_id).order_by(PageConfig.id)
    )
    configs = result.scalars().all()
    items = [
        {"page_key": c.page_key, "config_data": c.config_data, "status": c.status, "id": c.id}
        for c in configs
    ]
    return ResponseModel.success(data=items)


@router.get("/page-configs/{page_key}", summary="页面配置详情")
async def get_page_config_admin(
    page_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取指定页面配置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(PageConfig.page_key == page_key, PageConfig.is_deleted.is_(False), PageConfig.site_id == site_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return ResponseModel.success(data={"page_key": page_key, "config_data": {}})
    return ResponseModel.success(data={"page_key": config.page_key, "config_data": config.config_data, "status": config.status})


@router.put("/page-configs/{page_key}", summary="更新页面配置")
async def update_page_config_admin(
    page_key: str,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新页面配置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(PageConfig.page_key == page_key, PageConfig.is_deleted.is_(False), PageConfig.site_id == site_id)
    )
    config = result.scalar_one_or_none()
    if config:
        config.config_data = body.get("config_data", body)
    else:
        config = PageConfig(page_key=page_key, config_data=body.get("config_data", body), status="active", site_id=site_id)
        db.add(config)
    await db.commit()
    return ResponseModel.success(message="页面配置更新成功")


# ========== 系统设置 ==========

@router.get("/settings", summary="系统设置")
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取系统设置（存储在 page_config 表中，page_key='system_settings'）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(PageConfig.page_key == "system_settings", PageConfig.site_id == site_id)
    )
    config = result.scalar_one_or_none()
    return ResponseModel.success(data=config.config_data if config else {})


@router.put("/settings", summary="更新系统设置")
async def update_settings(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新系统设置"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(PageConfig.page_key == "system_settings", PageConfig.site_id == site_id)
    )
    config = result.scalar_one_or_none()
    if config:
        config.config_data = body
    else:
        config = PageConfig(page_key="system_settings", config_data=body, status="active", site_id=site_id)
        db.add(config)
    await db.commit()
    return ResponseModel.success(message="系统设置更新成功")


# ========== 免责声明管理 ==========

@router.get("/disclaimer-templates", summary="免责声明模板列表")
async def list_disclaimer_templates(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取免责声明模板列表"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(DisclaimerTemplate).where(DisclaimerTemplate.is_deleted.is_(False), DisclaimerTemplate.site_id == site_id).order_by(DisclaimerTemplate.id)
    )
    templates = result.scalars().all()
    items = [
        {"id": t.id, "title": t.title, "content": t.content, "version": t.version, "status": t.status}
        for t in templates
    ]
    return ResponseModel.success(data=items)


@router.put("/disclaimer-templates/{template_id}", summary="更新免责声明模板")
async def update_disclaimer_template(
    template_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新免责声明模板"""
    import hashlib

    result = await db.execute(
        select(DisclaimerTemplate).where(DisclaimerTemplate.id == template_id, DisclaimerTemplate.is_deleted.is_(False))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="免责声明模板不存在")
    if "content" in body:
        template.content = body["content"]
        template.content_hash = hashlib.sha256(body["content"].encode()).hexdigest()
        template.version += 1
    if "title" in body:
        template.title = body["title"]
    await db.commit()
    return ResponseModel.success(message="免责声明模板更新成功")


# ========== 通知管理（管理端） ==========

@router.get("/notifications/templates", summary="通知模板列表")
async def list_notification_templates(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取通知模板列表（使用 Notification 的 type 字段作为模板分类）"""
    # 通知模板没有专用模型，返回预定义列表
    templates = [
        {"id": 1, "key": "order_paid", "name": "订单支付成功", "channel": "wechat_subscribe", "status": "active"},
        {"id": 2, "key": "order_refunded", "name": "退款通知", "channel": "wechat_subscribe", "status": "active"},
        {"id": 3, "key": "ticket_verified", "name": "验票成功", "channel": "wechat_subscribe", "status": "active"},
        {"id": 4, "key": "booking_reminder", "name": "入园提醒", "channel": "wechat_subscribe", "status": "active"},
        {"id": 5, "key": "annual_card_expiring", "name": "年卡到期提醒", "channel": "wechat_subscribe", "status": "active"},
        {"id": 6, "key": "points_change", "name": "积分变动通知", "channel": "in_app", "status": "active"},
        {"id": 7, "key": "system_notice", "name": "系统公告", "channel": "in_app", "status": "active"},
    ]
    return ResponseModel.success(data=templates)


@router.put("/notifications/templates/{template_id}", summary="更新通知模板")
async def update_notification_template(
    template_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新通知模板（占位）"""
    return ResponseModel.success(message="通知模板更新成功")


@router.get("/notifications/records", summary="通知发送记录")
async def list_notification_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    template_key: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取通知发送记录"""
    conditions = [Notification.is_deleted.is_(False)]
    if template_key:
        conditions.append(Notification.type == template_key)
    if status:
        conditions.append(Notification.send_status == status)

    count_result = await db.execute(select(func.count(Notification.id)).where(*conditions))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = result.scalars().all()
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "type": r.type,
            "title": r.title,
            "content": r.content,
            "channel": r.channel,
            "send_status": r.send_status,
            "send_at": r.send_at.isoformat() if r.send_at else None,
            "is_read": r.is_read,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/notifications/stats", summary="通知统计")
async def get_notification_stats(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """通知发送统计"""
    total_result = await db.execute(select(func.count(Notification.id)).where(Notification.is_deleted.is_(False)))
    total = total_result.scalar() or 0

    sent_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.send_status == "sent", Notification.is_deleted.is_(False))
    )
    sent = sent_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.send_status == "failed", Notification.is_deleted.is_(False))
    )
    failed = failed_result.scalar() or 0

    read_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.is_read.is_(True), Notification.is_deleted.is_(False))
    )
    read = read_result.scalar() or 0

    return ResponseModel.success(data={
        "total": total,
        "sent": sent,
        "failed": failed,
        "pending": total - sent - failed,
        "read": read,
        "read_rate": round(read / total * 100, 2) if total > 0 else 0,
    })


# ========== 二次确认 ==========

@router.post("/confirm/verify-code", summary="验证确认码")
async def verify_confirm_code(
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """验证二次确认码（简单实现）"""
    code = body.get("code", "")
    action = body.get("action", "")
    # 简单验证：code 不为空即通过
    if not code:
        raise HTTPException(status_code=400, detail="确认码不能为空")
    return ResponseModel.success(data={"verified": True, "action": action}, message="验证通过")


@router.post("/confirm/verify-password", summary="验证操作密码")
async def verify_operation_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """验证操作密码"""
    import hashlib

    password = body.get("password", "")
    action = body.get("action", "")
    if not password:
        raise HTTPException(status_code=400, detail="操作密码不能为空")

    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    if admin.operation_password_hash and admin.operation_password_hash != pwd_hash:
        raise HTTPException(status_code=403, detail="操作密码错误")
    return ResponseModel.success(data={"verified": True, "action": action}, message="验证通过")


# ========== 会员详情 & 积分调整 ==========

@router.get("/members/{user_id}", summary="会员详情")
async def get_member_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取会员详情"""
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取年卡信息
    card_result = await db.execute(
        select(AnnualCard).where(AnnualCard.user_id == user_id, AnnualCard.is_deleted.is_(False))
    )
    annual_card = card_result.scalar_one_or_none()

    # 获取次数卡
    times_result = await db.execute(
        select(TimesCard).where(TimesCard.user_id == user_id, TimesCard.is_deleted.is_(False))
    )
    times_cards = times_result.scalars().all()

    return ResponseModel.success(data={
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "phone": user.phone,
        "member_level": user.member_level,
        "total_points": user.total_points,
        "available_points": user.available_points,
        "total_spent": float(user.total_spent) if user.total_spent else 0,
        "order_count": user.order_count,
        "annual_card": {
            "id": annual_card.id,
            "status": annual_card.status,
            "start_date": annual_card.start_date.isoformat() if annual_card.start_date else None,
            "end_date": annual_card.end_date.isoformat() if annual_card.end_date else None,
        } if annual_card else None,
        "times_cards": [
            {"id": tc.id, "remaining_times": tc.remaining_times, "status": tc.status}
            for tc in times_cards
        ],
        "created_at": user.created_at.isoformat() if user.created_at else None,
    })


@router.post("/members/{user_id}/points-adjust", summary="积分调整")
async def adjust_member_points(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端积分调整"""
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    points = body.get("points", 0)
    reason = body.get("reason", "管理员调整")

    user.available_points = (user.available_points or 0) + points
    if points > 0:
        user.total_points = (user.total_points or 0) + points

    await db.commit()
    return ResponseModel.success(
        data={"available_points": user.available_points, "total_points": user.total_points},
        message=f"积分调整成功：{'+' if points > 0 else ''}{points}",
    )


# ========== 年卡列表 ==========

@router.get("/annual-cards", summary="年卡列表")
async def list_annual_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取年卡列表"""
    conditions = [AnnualCard.is_deleted.is_(False)]
    if status:
        conditions.append(AnnualCard.status == status)

    count_result = await db.execute(select(func.count(AnnualCard.id)).where(*conditions))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(AnnualCard, User.nickname, User.phone)
        .join(User, User.id == AnnualCard.user_id, isouter=True)
        .where(*conditions)
        .order_by(AnnualCard.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for row in result.all():
        card = row[0]
        items.append({
            "id": card.id,
            "user_id": card.user_id,
            "user_nickname": row[1],
            "user_phone": row[2],
            "config_id": card.config_id,
            "status": card.status,
            "start_date": card.start_date.isoformat() if card.start_date else None,
            "end_date": card.end_date.isoformat() if card.end_date else None,
            "created_at": card.created_at.isoformat() if card.created_at else None,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


# ========== 次数卡消费规则 ==========

@router.get("/times-card-configs/{config_id}/consumption-rules", summary="次数卡消费规则")
async def get_consumption_rules(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取次数卡消费规则"""
    result = await db.execute(
        select(TimesCardConfig).where(TimesCardConfig.id == config_id, TimesCardConfig.is_deleted.is_(False))
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="次数卡配置不存在")
    # 消费规则存储在 applicable_products 字段中
    return ResponseModel.success(data=config.applicable_products or [])


@router.post("/times-card-configs/{config_id}/consumption-rules", summary="更新次数卡消费规则")
async def update_consumption_rules(
    config_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新次数卡消费规则"""
    result = await db.execute(
        select(TimesCardConfig).where(TimesCardConfig.id == config_id, TimesCardConfig.is_deleted.is_(False))
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="次数卡配置不存在")
    config.applicable_products = body.get("rules", [])
    await db.commit()
    return ResponseModel.success(message="消费规则更新成功")


# ========== 激活码导出 ==========

@router.post("/activation-codes/export", summary="导出激活码")
async def export_activation_codes(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """导出激活码（返回数据，前端处理下载）"""
    site_id = get_site_id(request)
    conditions = [ActivationCode.is_deleted.is_(False), ActivationCode.site_id == site_id]
    if body.get("batch_no"):
        conditions.append(ActivationCode.batch_no == body["batch_no"])
    if body.get("status"):
        conditions.append(ActivationCode.status == body["status"])

    result = await db.execute(
        select(ActivationCode).where(*conditions).order_by(ActivationCode.id)
    )
    codes = result.scalars().all()
    items = [
        {"code": c.code, "batch_no": c.batch_no, "status": c.status,
         "used_by": c.used_by, "used_at": c.used_at.isoformat() if c.used_at else None}
        for c in codes
    ]
    return ResponseModel.success(data=items, message=f"共 {len(items)} 条激活码")


# ========== 次数卡列表 & 调整 ==========

@router.get("/times-cards", summary="次数卡列表")
async def list_times_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取次数卡列表"""
    count_result = await db.execute(
        select(func.count(TimesCard.id)).where(TimesCard.is_deleted.is_(False))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(TimesCard, User.nickname, User.phone)
        .join(User, User.id == TimesCard.user_id, isouter=True)
        .where(TimesCard.is_deleted.is_(False))
        .order_by(TimesCard.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for row in result.all():
        card = row[0]
        items.append({
            "id": card.id,
            "user_id": card.user_id,
            "user_nickname": row[1],
            "user_phone": row[2],
            "config_id": card.config_id,
            "remaining_times": card.remaining_times,
            "used_times": card.used_times,
            "status": card.status,
            "expire_at": card.expire_at.isoformat() if card.expire_at else None,
            "created_at": card.created_at.isoformat() if card.created_at else None,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.put("/times-cards/{card_id}/adjust", summary="调整次数卡")
async def adjust_times_card(
    card_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """调整次数卡次数"""
    result = await db.execute(
        select(TimesCard).where(TimesCard.id == card_id, TimesCard.is_deleted.is_(False))
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="次数卡不存在")
    adjust = body.get("adjust_times", 0)
    card.remaining_times = (card.remaining_times or 0) + adjust
    await db.commit()
    return ResponseModel.success(
        data={"remaining_times": card.remaining_times},
        message=f"次数调整成功：{'+' if adjust > 0 else ''}{adjust}",
    )


# ========== 商品定价规则管理 ==========

@router.get("/products/{product_id}/pricing-rules", summary="商品定价规则列表")
async def list_product_pricing_rules(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取商品定价规则"""
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.product_id == product_id,
            PricingRule.is_deleted.is_(False),
        ).order_by(PricingRule.id)
    )
    rules = result.scalars().all()
    items = []
    for r in rules:
        items.append({
            "id": r.id,
            "product_id": r.product_id,
            "rule_type": r.rule_type,
            "date_type": r.date_type,
            "date_start": r.date_start.isoformat() if r.date_start else None,
            "date_end": r.date_end.isoformat() if r.date_end else None,
            "price": float(r.price) if r.price else None,
            "status": r.status,
        })
    return ResponseModel.success(data=items)


@router.post("/products/{product_id}/pricing-rules", summary="创建商品定价规则")
async def create_product_pricing_rule(
    product_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建商品定价规则"""
    rule = PricingRule(
        product_id=product_id,
        rule_type=body.get("rule_type", "date_range"),
        date_type=body.get("date_type"),
        date_start=date.fromisoformat(body["date_start"]) if body.get("date_start") else None,
        date_end=date.fromisoformat(body["date_end"]) if body.get("date_end") else None,
        price=Decimal(str(body["price"])) if body.get("price") else None,
        status=body.get("status", "active"),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ResponseModel.success(data={"id": rule.id}, message="定价规则创建成功")


@router.put("/products/{product_id}/pricing-rules/{rule_id}", summary="更新商品定价规则")
async def update_product_pricing_rule(
    product_id: int,
    rule_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新商品定价规则"""
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.id == rule_id, PricingRule.product_id == product_id,
            PricingRule.is_deleted.is_(False),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="定价规则不存在")
    for field in ["rule_type", "date_type", "status"]:
        if field in body:
            setattr(rule, field, body[field])
    if "price" in body:
        rule.price = Decimal(str(body["price"]))
    if "date_start" in body:
        rule.date_start = date.fromisoformat(body["date_start"]) if body["date_start"] else None
    if "date_end" in body:
        rule.date_end = date.fromisoformat(body["date_end"]) if body["date_end"] else None
    await db.commit()
    return ResponseModel.success(message="定价规则更新成功")


@router.delete("/products/{product_id}/pricing-rules/{rule_id}", summary="删除商品定价规则")
async def delete_product_pricing_rule(
    product_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除商品定价规则（软删除）"""
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.id == rule_id, PricingRule.product_id == product_id,
            PricingRule.is_deleted.is_(False),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="定价规则不存在")
    rule.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="定价规则已删除")


# ========== 商品优惠规则管理 ==========

@router.get("/products/{product_id}/discount-rules", summary="优惠规则列表")
async def list_product_discount_rules(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取商品优惠规则"""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.product_id == product_id,
            DiscountRule.is_deleted.is_(False),
        ).order_by(DiscountRule.id)
    )
    rules = result.scalars().all()
    items = []
    for r in rules:
        items.append({
            "id": r.id,
            "product_id": r.product_id,
            "rule_type": r.rule_type,
            "threshold": r.threshold,
            "discount_rate": float(r.discount_rate) if r.discount_rate else None,
            "status": r.status,
        })
    return ResponseModel.success(data=items)


@router.post("/products/{product_id}/discount-rules", summary="创建优惠规则")
async def create_product_discount_rule(
    product_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建商品优惠规则"""
    rule = DiscountRule(
        product_id=product_id,
        rule_type=body.get("rule_type", "quantity"),
        threshold=body.get("threshold", 0),
        discount_rate=Decimal(str(body["discount_rate"])) if body.get("discount_rate") else None,
        status=body.get("status", "active"),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ResponseModel.success(data={"id": rule.id}, message="优惠规则创建成功")


@router.put("/products/{product_id}/discount-rules/{rule_id}", summary="更新优惠规则")
async def update_product_discount_rule(
    product_id: int,
    rule_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新商品优惠规则"""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.id == rule_id, DiscountRule.product_id == product_id,
            DiscountRule.is_deleted.is_(False),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="优惠规则不存在")
    for field in ["rule_type", "threshold", "status"]:
        if field in body:
            setattr(rule, field, body[field])
    if "discount_rate" in body:
        rule.discount_rate = Decimal(str(body["discount_rate"]))
    await db.commit()
    return ResponseModel.success(message="优惠规则更新成功")


@router.delete("/products/{product_id}/discount-rules/{rule_id}", summary="删除优惠规则")
async def delete_product_discount_rule(
    product_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除商品优惠规则（软删除）"""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.id == rule_id, DiscountRule.product_id == product_id,
            DiscountRule.is_deleted.is_(False),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="优惠规则不存在")
    rule.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="优惠规则已删除")


# ========== 库存管理 ==========

@router.get("/inventory", summary="库存列表")
async def list_inventory(
    product_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取库存列表"""
    conditions = [Inventory.is_deleted.is_(False)]
    if product_id:
        conditions.append(Inventory.product_id == product_id)
    if start_date:
        conditions.append(Inventory.date >= date.fromisoformat(start_date))
    if end_date:
        conditions.append(Inventory.date <= date.fromisoformat(end_date))

    count_result = await db.execute(select(func.count(Inventory.id)).where(*conditions))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Inventory, Product.name.label("product_name"))
        .join(Product, Product.id == Inventory.product_id, isouter=True)
        .where(*conditions)
        .order_by(Inventory.date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for row in result.all():
        inv = row[0]
        items.append({
            "id": inv.id,
            "product_id": inv.product_id,
            "product_name": row[1],
            "date": inv.date.isoformat() if inv.date else None,
            "total": inv.total,
            "locked": inv.locked,
            "sold": inv.sold,
            "available": (inv.total or 0) - (inv.locked or 0) - (inv.sold or 0),
            "status": inv.status,
        })
    return ResponseModel.success(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.put("/inventory/{inventory_id}", summary="更新库存")
async def update_inventory(
    inventory_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新库存"""
    result = await db.execute(
        select(Inventory).where(Inventory.id == inventory_id, Inventory.is_deleted.is_(False))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    if "total" in body:
        inv.total = body["total"]
    if "status" in body:
        inv.status = body["status"]
    await db.commit()
    return ResponseModel.success(message="库存更新成功")


@router.post("/inventory/batch-open", summary="批量开放库存")
async def batch_open_inventory(
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """批量开放库存"""
    product_id = body.get("product_id")
    start = body.get("start_date")
    end = body.get("end_date")
    total_per_day = body.get("total", 10)

    if not all([product_id, start, end]):
        raise HTTPException(status_code=400, detail="请提供 product_id、start_date、end_date")

    dt_start = date.fromisoformat(start)
    dt_end = date.fromisoformat(end)
    created = 0
    current = dt_start
    while current <= dt_end:
        # 检查是否已有
        exist = await db.execute(
            select(Inventory).where(Inventory.product_id == product_id, Inventory.date == current)
        )
        if not exist.scalar_one_or_none():
            inv = Inventory(product_id=product_id, date=current, total=total_per_day, locked=0, sold=0, status="open")
            db.add(inv)
            created += 1
        current += timedelta(days=1)

    await db.commit()
    return ResponseModel.success(data={"created": created}, message=f"成功开放 {created} 天库存")


# ========== 押金记录 ==========

@router.get("/finance/deposits", summary="押金记录列表")
async def list_deposit_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取押金记录列表（从订单中筛选包含押金的项目）"""
    # 简单实现：返回空列表占位，需要有 Deposit 模型后完善
    return ResponseModel.success(data={"items": [], "total": 0, "page": page, "page_size": page_size})


# ========== 订单退款审批（兼容前端路径） ==========

@router.post("/orders/{order_id}/refund/approve", summary="退款审批")
async def approve_order_refund(
    order_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """退款审批（兼容前端 /refund/approve 路径）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.is_deleted.is_(False), Order.site_id == site_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    approved = body.get("approved", False)
    reason = body.get("reason", "")

    if approved:
        order.status = "refunded"
    else:
        order.status = "paid"  # 拒绝退款恢复到已支付

    await db.commit()
    msg = "退款已通过" if approved else "退款已拒绝"
    return ResponseModel.success(message=msg)


@router.post("/orders/{order_id}/partial-refund", summary="部分退款")
async def partial_refund(
    order_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """部分退款"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.is_deleted.is_(False), Order.site_id == site_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # 简单标记为部分退款
    order.status = "partial_refunded"
    await db.commit()
    return ResponseModel.success(message="部分退款处理成功")


# ========== 商品状态更新（兼容 PUT 方法） ==========

@router.put("/products/{product_id}/status", summary="更新商品状态")
async def update_product_status_put(
    product_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新商品上下架状态（PUT方法兼容）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted.is_(False), Product.site_id == site_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.status = body.get("status", product.status)
    await db.commit()
    return ResponseModel.success(message="商品状态更新成功")


# ========== 商品删除 ==========

@router.delete("/products/{product_id}", summary="删除商品")
async def delete_product(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除商品（软删除）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted.is_(False), Product.site_id == site_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="商品已删除")


# ========== 管理端订单详情 ==========

@router.get("/orders/{order_id}", summary="管理端订单详情")
async def admin_get_order_detail(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端获取订单详情"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.is_deleted.is_(False), Order.site_id == site_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 获取订单项
    items_result = await db.execute(
        select(OrderItem, Product.name.label("product_name"))
        .join(Product, Product.id == OrderItem.product_id, isouter=True)
        .where(OrderItem.order_id == order_id)
    )
    order_items = []
    for row in items_result.all():
        item = row[0]
        order_items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": row[1],
            "quantity": item.quantity,
            "unit_price": float(item.unit_price) if item.unit_price else 0,
            "subtotal": float(item.subtotal) if item.subtotal else 0,
            "use_date": item.use_date.isoformat() if item.use_date else None,
        })

    # 获取用户信息
    user_result = await db.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()

    return ResponseModel.success(data={
        "id": order.id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "user_nickname": user.nickname if user else None,
        "user_phone": user.phone if user else None,
        "status": order.status,
        "total_amount": float(order.total_amount) if order.total_amount else 0,
        "payment_method": order.payment_method,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "items": order_items,
        "remark": order.remark,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    })
