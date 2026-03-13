"""
营位管理路由（独立品类，从商品管理中拆分）

B端 /api/v1/admin/campsites：
- GET / — 营位列表（含扩展信息、库存概况）
- GET /{id} — 营位详情
- POST / — 创建营位
- PUT /{id} — 更新营位
- PATCH /{id}/status — 上架/下架
- GET /{id}/inventory — 营位库存日历
- POST /{id}/inventory/batch — 批量开放库存
- GET /{id}/pricing-rules — 定价规则
- POST /{id}/pricing-rules — 创建定价规则
- PUT /{id}/pricing-rules/{rule_id} — 更新定价规则
- DELETE /{id}/pricing-rules/{rule_id} — 删除定价规则
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from models.product import (
    Inventory,
    PricingRule,
    Product,
    ProductExtCamping,
)
from schemas.common import PaginationParams, ResponseModel
from services import product_service

router = APIRouter(prefix="/api/v1/admin/campsites", tags=["营位管理"])

# 营位类型白名单
CAMPSITE_TYPES = ("daily_camping", "event_camping")


# ========== 统计概览（必须在 /{campsite_id} 之前定义，避免路径被拦截） ==========

@router.get("/stats/overview", summary="营位统计概览")
async def get_campsite_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """营位统计概览：各类型数量、在售/下架数量、今日库存概况"""
    site_id = get_site_id(request)
    today = date.today()

    # 各类型数量
    type_counts = await db.execute(
        select(
            Product.type,
            Product.status,
            func.count(Product.id),
        )
        .where(
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
        .group_by(Product.type, Product.status)
    )

    stats: Dict[str, Any] = {
        "daily_camping": {"total": 0, "on_sale": 0, "off_sale": 0, "draft": 0},
        "event_camping": {"total": 0, "on_sale": 0, "off_sale": 0, "draft": 0},
    }
    total_count = 0
    on_sale_count = 0

    for ptype, pstatus, count in type_counts.all():
        if ptype in stats:
            stats[ptype][pstatus] = count
            stats[ptype]["total"] += count
            total_count += count
            if pstatus == "on_sale":
                on_sale_count += count

    # 今日库存概况
    today_inv = await db.execute(
        select(
            func.sum(Inventory.total),
            func.sum(Inventory.available),
            func.sum(Inventory.sold),
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Product.type.in_(CAMPSITE_TYPES),
            Product.site_id == site_id,
            Inventory.date == today,
            Inventory.is_deleted.is_(False),
        )
    )
    today_total, today_available, today_sold = today_inv.one()

    return ResponseModel.success(data={
        "total_campsites": total_count,
        "on_sale": on_sale_count,
        "type_stats": stats,
        "today_inventory": {
            "total": int(today_total or 0),
            "available": int(today_available or 0),
            "sold": int(today_sold or 0),
            "occupancy_rate": round(
                int(today_sold or 0) / int(today_total or 1) * 100, 1
            ) if today_total else 0,
        },
    })


@router.get("/", summary="营位列表")
async def list_campsites(
    request: Request,
    keyword: Optional[str] = Query(None, description="搜索关键词（名称/区域/编号）"),
    campsite_type: Optional[str] = Query(None, description="营位类型: daily_camping/event_camping"),
    area: Optional[str] = Query(None, description="区域筛选"),
    status: Optional[str] = Query(None, description="状态: on_sale/off_sale/draft"),
    has_electricity: Optional[bool] = Query(None, description="有电"),
    has_platform: Optional[bool] = Query(None, description="有木平台"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """营位列表（含扩展属性、库存概况）"""
    site_id = get_site_id(request)
    # 基础条件：仅查营位类型商品 + site_id 过滤
    query = (
        select(Product)
        .outerjoin(ProductExtCamping, Product.id == ProductExtCamping.product_id)
        .where(
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )

    # 名称/区域/编号搜索
    if keyword:
        from sqlalchemy import or_
        like = f"%{keyword}%"
        query = query.where(
            or_(
                Product.name.ilike(like),
                ProductExtCamping.area.ilike(like),
                ProductExtCamping.position_name.ilike(like),
            )
        )

    if campsite_type and campsite_type in CAMPSITE_TYPES:
        query = query.where(Product.type == campsite_type)
    if status:
        query = query.where(Product.status == status)
    if area:
        query = query.where(ProductExtCamping.area == area)
    if has_electricity is not None:
        query = query.where(ProductExtCamping.has_electricity == has_electricity)
    if has_platform is not None:
        query = query.where(ProductExtCamping.has_platform == has_platform)

    # 总数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # 分页 + 排序
    query = (
        query
        .options(selectinload(Product.ext_camping))
        .order_by(Product.sort_order.asc(), Product.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    result = await db.execute(query)
    campsites = result.scalars().unique().all()

    # 批量查询今日及未来7天库存概况
    product_ids = [c.id for c in campsites]
    today = date.today()
    week_end = today + timedelta(days=7)

    stock_summary: Dict[int, Dict[str, int]] = {}
    if product_ids:
        inv_result = await db.execute(
            select(
                Inventory.product_id,
                func.sum(Inventory.total).label("total"),
                func.sum(Inventory.locked + Inventory.sold).label("booked"),
                func.sum(Inventory.available).label("available"),
            )
            .where(
                Inventory.product_id.in_(product_ids),
                Inventory.date >= today,
                Inventory.date <= week_end,
                Inventory.is_deleted.is_(False),
            )
            .group_by(Inventory.product_id)
        )
        for row in inv_result.all():
            stock_summary[row.product_id] = {
                "total_7d": int(row.total or 0),
                "booked_7d": int(row.booked or 0),
                "available_7d": int(row.available or 0),
            }

    # 查询区域列表（供前端筛选用）
    area_result = await db.execute(
        select(ProductExtCamping.area)
        .where(ProductExtCamping.area.isnot(None))
        .distinct()
    )
    areas = [r[0] for r in area_result.all() if r[0]]

    items = []
    for c in campsites:
        ext = c.ext_camping
        stock = stock_summary.get(c.id, {"total_7d": 0, "booked_7d": 0, "available_7d": 0})
        items.append({
            "id": c.id,
            "name": c.name,
            "type": c.type,
            "type_label": "日常营位" if c.type == "daily_camping" else "活动营位",
            "status": c.status,
            "base_price": str(c.base_price),
            "booking_mode": c.booking_mode,
            "sort_order": c.sort_order,
            "images": c.images,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            # 营位扩展属性
            "area": ext.area if ext else None,
            "position_name": ext.position_name if ext else None,
            "has_electricity": ext.has_electricity if ext else False,
            "has_platform": ext.has_platform if ext else False,
            "sun_exposure": ext.sun_exposure if ext else None,
            "max_persons": ext.max_persons if ext else None,
            "event_start_date": ext.event_start_date.isoformat() if ext and ext.event_start_date else None,
            "event_end_date": ext.event_end_date.isoformat() if ext and ext.event_end_date else None,
            # 库存概况
            "stock_summary": stock,
        })

    return ResponseModel.success(data={
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total_pages": (total + pagination.page_size - 1) // pagination.page_size,
        "areas": areas,
    })


@router.get("/{campsite_id}", summary="营位详情")
async def get_campsite_detail(
    campsite_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取营位详情（含扩展信息、定价规则）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.ext_camping),
            selectinload(Product.pricing_rules),
            selectinload(Product.discount_rules),
        )
        .where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    campsite = result.scalar_one_or_none()
    if not campsite:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    ext = campsite.ext_camping
    data = {
        "id": campsite.id,
        "name": campsite.name,
        "type": campsite.type,
        "status": campsite.status,
        "description": campsite.description,
        "base_price": str(campsite.base_price),
        "booking_mode": campsite.booking_mode,
        "images": campsite.images,
        "sort_order": campsite.sort_order,
        "category": campsite.category,
        "require_disclaimer": campsite.require_disclaimer,
        "require_camping_ticket": campsite.require_camping_ticket,
        "is_seckill": campsite.is_seckill,
        "normal_payment_timeout": campsite.normal_payment_timeout,
        "seckill_payment_timeout": campsite.seckill_payment_timeout,
        "refund_deadline_type": campsite.refund_deadline_type,
        "refund_deadline_value": campsite.refund_deadline_value,
        "sale_start_at": campsite.sale_start_at.isoformat() if campsite.sale_start_at else None,
        "sale_end_at": campsite.sale_end_at.isoformat() if campsite.sale_end_at else None,
        "created_at": campsite.created_at.isoformat() if campsite.created_at else None,
        "updated_at": campsite.updated_at.isoformat() if campsite.updated_at else None,
        # 营位扩展
        "ext_camping": {
            "area": ext.area,
            "position_name": ext.position_name,
            "has_electricity": ext.has_electricity,
            "has_platform": ext.has_platform,
            "sun_exposure": ext.sun_exposure,
            "max_persons": ext.max_persons,
            "event_start_date": ext.event_start_date.isoformat() if ext.event_start_date else None,
            "event_end_date": ext.event_end_date.isoformat() if ext.event_end_date else None,
        } if ext else None,
        # 定价规则
        "pricing_rules": [
            {
                "id": r.id,
                "rule_type": r.rule_type,
                "date_type": r.date_type,
                "custom_date": r.custom_date.isoformat() if r.custom_date else None,
                "price": str(r.price),
            }
            for r in (campsite.pricing_rules or [])
        ],
        # 优惠规则
        "discount_rules": [
            {
                "id": r.id,
                "rule_type": r.rule_type,
                "threshold": r.threshold,
                "discount_rate": str(r.discount_rate),
                "status": r.status,
            }
            for r in (campsite.discount_rules or [])
        ],
    }

    return ResponseModel.success(data=data)


@router.post("/", summary="创建营位")
async def create_campsite(
    request: Request,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建营位（自动设置 type 为 daily_camping/event_camping）"""
    site_id = get_site_id(request)
    campsite_type = body.get("type", "daily_camping")
    if campsite_type not in CAMPSITE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": f"营位类型必须是 {'/'.join(CAMPSITE_TYPES)}"},
        )

    # 确保 type 正确
    body["type"] = campsite_type
    body["site_id"] = site_id

    product = await product_service.create_product(db, body, operator_id=admin.id)
    await db.commit()

    return ResponseModel.success(
        data={"id": product.id, "name": product.name},
        message="营位创建成功",
    )


@router.put("/{campsite_id}", summary="更新营位")
async def update_campsite(
    campsite_id: int,
    request: Request,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新营位信息"""
    site_id = get_site_id(request)
    # 校验是营位类型
    existing = await db.execute(
        select(Product).where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    # 不允许修改 type 为非营位类型
    if "type" in body and body["type"] not in CAMPSITE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "不允许将营位类型修改为非营位类型"},
        )

    product = await product_service.update_product(db, campsite_id, body, operator_id=admin.id)
    await db.commit()

    return ResponseModel.success(
        data={"id": product.id, "name": product.name},
        message="营位更新成功",
    )


@router.patch("/{campsite_id}/status", summary="营位上架/下架")
async def update_campsite_status(
    campsite_id: int,
    request: Request,
    status: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """营位上架/下架"""
    site_id = get_site_id(request)
    existing = await db.execute(
        select(Product).where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    if status not in ("on_sale", "off_sale", "draft"):
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "状态值无效，可选: on_sale/off_sale/draft"},
        )

    product = await product_service.update_product_status(
        db, campsite_id, status, operator_id=admin.id,
    )
    await db.commit()

    return ResponseModel.success(
        data={"id": product.id, "status": product.status},
        message="营位状态更新成功",
    )


@router.delete("/{campsite_id}", summary="删除营位")
async def delete_campsite(
    campsite_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """软删除营位"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(Product).where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    campsite = result.scalar_one_or_none()
    if not campsite:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    campsite.is_deleted = True
    await db.commit()

    return ResponseModel.success(message="营位已删除")


# ========== 库存管理 ==========

@router.get("/{campsite_id}/inventory", summary="营位库存日历")
async def get_campsite_inventory(
    campsite_id: int,
    request: Request,
    date_start: date = Query(..., description="起始日期"),
    date_end: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """查看营位指定日期范围的库存"""
    site_id = get_site_id(request)
    # 校验是营位
    existing = await db.execute(
        select(Product).where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    inv_result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == campsite_id,
            Inventory.date >= date_start,
            Inventory.date <= date_end,
            Inventory.is_deleted.is_(False),
        ).order_by(Inventory.date.asc())
    )
    inventories = inv_result.scalars().all()

    items = [
        {
            "id": inv.id,
            "date": inv.date.isoformat(),
            "total": inv.total,
            "locked": inv.locked,
            "sold": inv.sold,
            "available": inv.available,
            "status": inv.status,
        }
        for inv in inventories
    ]

    return ResponseModel.success(data=items)


@router.post("/{campsite_id}/inventory/batch", summary="批量开放库存")
async def batch_open_inventory(
    campsite_id: int,
    request: Request,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """批量为营位开放指定日期范围的库存"""
    site_id = get_site_id(request)
    existing = await db.execute(
        select(Product).where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    start_date = date.fromisoformat(body["start_date"])
    end_date = date.fromisoformat(body["end_date"])
    total_stock = body.get("total_stock", 1)

    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "起始日期不能大于结束日期"},
        )

    created_count = 0
    current = start_date
    while current <= end_date:
        # 检查是否已存在
        existing_inv = await db.execute(
            select(Inventory).where(
                Inventory.product_id == campsite_id,
                Inventory.date == current,
                Inventory.is_deleted.is_(False),
            )
        )
        if not existing_inv.scalar_one_or_none():
            inv = Inventory(
                product_id=campsite_id,
                date=current,
                total=total_stock,
                locked=0,
                sold=0,
                available=total_stock,
                status="open",
            )
            db.add(inv)
            created_count += 1

        current += timedelta(days=1)

    await db.commit()

    return ResponseModel.success(
        data={"created_count": created_count},
        message=f"已开放 {created_count} 天库存",
    )


# ========== 定价规则 ==========

@router.get("/{campsite_id}/pricing-rules", summary="定价规则列表")
async def list_pricing_rules(
    campsite_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取营位的定价规则列表"""
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.product_id == campsite_id,
            PricingRule.is_deleted.is_(False),
        ).order_by(PricingRule.id.desc())
    )
    rules = result.scalars().all()

    items = [
        {
            "id": r.id,
            "rule_type": r.rule_type,
            "date_type": r.date_type,
            "custom_date": r.custom_date.isoformat() if r.custom_date else None,
            "price": str(r.price),
        }
        for r in rules
    ]

    return ResponseModel.success(data=items)


@router.post("/{campsite_id}/pricing-rules", summary="创建定价规则")
async def create_pricing_rule(
    campsite_id: int,
    request: Request,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """为营位创建定价规则"""
    site_id = get_site_id(request)
    # 校验是营位
    existing = await db.execute(
        select(Product).where(
            Product.id == campsite_id,
            Product.type.in_(CAMPSITE_TYPES),
            Product.is_deleted.is_(False),
            Product.site_id == site_id,
        )
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "营位不存在"})

    rule = PricingRule(
        product_id=campsite_id,
        rule_type=body.get("rule_type", "date_type"),
        date_type=body.get("date_type"),
        custom_date=date.fromisoformat(body["custom_date"]) if body.get("custom_date") else None,
        price=Decimal(str(body["price"])),
    )
    db.add(rule)
    await db.commit()

    return ResponseModel.success(
        data={"id": rule.id},
        message="定价规则创建成功",
    )


@router.put("/{campsite_id}/pricing-rules/{rule_id}", summary="更新定价规则")
async def update_pricing_rule(
    campsite_id: int,
    rule_id: int,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新营位的定价规则"""
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.id == rule_id,
            PricingRule.product_id == campsite_id,
            PricingRule.is_deleted.is_(False),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "定价规则不存在"})

    if "rule_type" in body:
        rule.rule_type = body["rule_type"]
    if "date_type" in body:
        rule.date_type = body["date_type"]
    if "custom_date" in body:
        rule.custom_date = date.fromisoformat(body["custom_date"]) if body["custom_date"] else None
    if "price" in body:
        rule.price = Decimal(str(body["price"]))

    await db.commit()
    return ResponseModel.success(message="定价规则更新成功")


@router.delete("/{campsite_id}/pricing-rules/{rule_id}", summary="删除定价规则")
async def delete_pricing_rule(
    campsite_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除营位的定价规则"""
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.id == rule_id,
            PricingRule.product_id == campsite_id,
            PricingRule.is_deleted.is_(False),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "定价规则不存在"})

    rule.is_deleted = True
    await db.commit()
    return ResponseModel.success(message="定价规则已删除")
