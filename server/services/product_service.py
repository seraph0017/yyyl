"""
商品服务

- list_products：商品列表（分页、筛选、搜索）
- get_product_detail：商品详情
- create_product：创建商品（管理端）
- update_product：更新商品（管理端）
- update_product_status：上架/下架
- batch_update_status：批量上架/下架
- get_price_calendar：价格日历
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.product import (
    DateTypeConfig,
    DiscountRule,
    Inventory,
    PricingRule,
    Product,
    ProductExtActivity,
    ProductExtCamping,
    ProductExtRental,
    ProductExtShop,
    SKU,
)

logger = logging.getLogger(__name__)

# 排序字段白名单（防SQL注入）
ALLOWED_SORT_FIELDS = {"id", "name", "base_price", "sort_order", "created_at", "updated_at"}


async def list_products(
    db: AsyncSession,
    *,
    site_id: Optional[int] = None,
    keyword: Optional[str] = None,
    product_type: Optional[str] = None,
    category: Optional[str] = None,
    product_status: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    is_seckill: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[Product], int]:
    """商品列表查询

    Args:
        db: 数据库会话
        site_id: 营地ID（SQL WHERE 过滤）
        keyword: 搜索关键词
        product_type: 商品类型筛选
        category: 分类筛选
        product_status: 状态筛选（默认只返回 on_sale）
        min_price: 最低价
        max_price: 最高价
        is_seckill: 是否秒杀
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向 asc/desc

    Returns:
        (商品列表, 总数)
    """
    query = select(Product).where(Product.is_deleted.is_(False))

    if site_id is not None:
        query = query.where(Product.site_id == site_id)

    # 筛选条件
    if keyword:
        query = query.where(
            or_(
                Product.name.ilike(f"%{keyword}%"),
                Product.description.ilike(f"%{keyword}%"),
            )
        )
    if product_type:
        query = query.where(Product.type == product_type)
    if category:
        query = query.where(Product.category == category)
    if product_status:
        query = query.where(Product.status == product_status)
    if min_price is not None:
        query = query.where(Product.base_price >= min_price)
    if max_price is not None:
        query = query.where(Product.base_price <= max_price)
    if is_seckill is not None:
        query = query.where(Product.is_seckill == is_seckill)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(Product, sort_by)
        query = query.order_by(order_col.desc() if sort_order == "desc" else order_col.asc())
    else:
        query = query.order_by(Product.sort_order.asc(), Product.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    products = list(result.scalars().all())

    return products, total


async def get_product_detail(
    db: AsyncSession,
    product_id: int,
) -> Product:
    """获取商品详情

    Args:
        db: 数据库会话
        product_id: 商品ID

    Returns:
        Product 模型实例

    Raises:
        HTTPException 40401: 商品不存在
    """
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.pricing_rules),
            selectinload(Product.discount_rules),
        )
        .where(Product.id == product_id, Product.is_deleted.is_(False))
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "商品不存在"},
        )

    return product


async def create_product(
    db: AsyncSession,
    data: Dict[str, Any],
    operator_id: int,
) -> Product:
    """创建商品

    Args:
        db: 数据库会话
        data: 商品数据
        operator_id: 操作人ID

    Returns:
        创建的 Product 实例
    """
    # 提取扩展信息和SKU
    ext_camping_data = data.pop("ext_camping", None)
    ext_rental_data = data.pop("ext_rental", None)
    ext_activity_data = data.pop("ext_activity", None)
    ext_shop_data = data.pop("ext_shop", None)
    skus_data = data.pop("skus", [])

    # 创建商品主体
    product = Product(**data)
    db.add(product)
    await db.flush()

    # 创建扩展表
    product_type = data.get("type", "")
    if ext_camping_data and product_type in ("daily_camping", "event_camping"):
        ext = ProductExtCamping(product_id=product.id, **ext_camping_data)
        db.add(ext)
    elif ext_rental_data and product_type == "rental":
        ext = ProductExtRental(product_id=product.id, **ext_rental_data)
        db.add(ext)
    elif ext_activity_data and product_type in ("daily_activity", "special_activity"):
        ext = ProductExtActivity(product_id=product.id, **ext_activity_data)
        db.add(ext)
    elif ext_shop_data and product_type in ("shop", "merchandise"):
        ext = ProductExtShop(product_id=product.id, **ext_shop_data)
        db.add(ext)

    # 创建SKU
    for sku_data in skus_data:
        sku = SKU(product_id=product.id, **sku_data)
        db.add(sku)

    await db.flush()
    logger.info(f"[商品] 创建商品: id={product.id}, name={product.name}, operator={operator_id}")

    return product


async def update_product(
    db: AsyncSession,
    product_id: int,
    data: Dict[str, Any],
    operator_id: int,
) -> Product:
    """更新商品

    Args:
        db: 数据库会话
        product_id: 商品ID
        data: 更新数据（已过滤 None 值）
        operator_id: 操作人ID

    Returns:
        更新后的 Product 实例
    """
    product = await get_product_detail(db, product_id)

    # 提取扩展数据
    ext_camping_data = data.pop("ext_camping", None)
    ext_rental_data = data.pop("ext_rental", None)
    ext_activity_data = data.pop("ext_activity", None)
    ext_shop_data = data.pop("ext_shop", None)

    # 更新主体字段
    for key, value in data.items():
        if hasattr(product, key) and value is not None:
            setattr(product, key, value)

    # 更新扩展表
    if ext_camping_data and product.ext_camping:
        for k, v in ext_camping_data.items():
            setattr(product.ext_camping, k, v)
    if ext_rental_data and product.ext_rental:
        for k, v in ext_rental_data.items():
            setattr(product.ext_rental, k, v)
    if ext_activity_data and product.ext_activity:
        for k, v in ext_activity_data.items():
            setattr(product.ext_activity, k, v)
    if ext_shop_data and product.ext_shop:
        for k, v in ext_shop_data.items():
            setattr(product.ext_shop, k, v)

    await db.flush()
    logger.info(f"[商品] 更新商品: id={product_id}, operator={operator_id}")

    return product


async def update_product_status(
    db: AsyncSession,
    product_id: int,
    new_status: str,
    operator_id: int,
) -> Product:
    """上架/下架商品

    Args:
        db: 数据库会话
        product_id: 商品ID
        new_status: 目标状态 on_sale / off_sale
        operator_id: 操作人ID

    Returns:
        更新后的 Product 实例
    """
    product = await get_product_detail(db, product_id)
    product.status = new_status
    await db.flush()

    logger.info(f"[商品] 状态变更: id={product_id}, status={new_status}, operator={operator_id}")
    return product


async def batch_update_status(
    db: AsyncSession,
    product_ids: List[int],
    new_status: str,
    operator_id: int,
) -> int:
    """批量上架/下架

    Args:
        db: 数据库会话
        product_ids: 商品ID列表
        new_status: 目标状态
        operator_id: 操作人ID

    Returns:
        更新数量
    """
    result = await db.execute(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.is_deleted.is_(False),
        )
    )
    products = list(result.scalars().all())

    for p in products:
        p.status = new_status

    await db.flush()
    logger.info(
        f"[商品] 批量状态变更: ids={product_ids}, status={new_status}, "
        f"count={len(products)}, operator={operator_id}"
    )
    return len(products)


async def get_price_calendar(
    db: AsyncSession,
    product_id: int,
    date_start: date,
    date_end: date,
) -> List[Dict[str, Any]]:
    """获取价格日历

    Args:
        db: 数据库会话
        product_id: 商品ID
        date_start: 起始日期
        date_end: 结束日期

    Returns:
        日期价格列表
    """
    product = await get_product_detail(db, product_id)

    # 获取定价规则
    pricing_rules = product.pricing_rules if product.pricing_rules else []

    # 获取日期类型配置
    dtc_result = await db.execute(
        select(DateTypeConfig).where(
            DateTypeConfig.date >= date_start,
            DateTypeConfig.date <= date_end,
        )
    )
    date_type_configs = {dtc.date: dtc.date_type for dtc in dtc_result.scalars().all()}

    # 获取库存
    inv_result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.date >= date_start,
            Inventory.date <= date_end,
            Inventory.is_deleted.is_(False),
        )
    )
    inventory_map = {inv.date: inv for inv in inv_result.scalars().all()}

    # 构建规则映射
    date_type_rules = {}  # date_type -> price
    custom_date_rules = {}  # date -> price
    for rule in pricing_rules:
        if rule.rule_type == "date_type" and rule.date_type:
            date_type_rules[rule.date_type] = rule.price
        elif rule.rule_type == "custom_date" and rule.custom_date:
            custom_date_rules[rule.custom_date] = rule.price

    # 构建日历
    calendar = []
    current = date_start
    while current <= date_end:
        # 确定日期类型
        if current in date_type_configs:
            dt = date_type_configs[current]
        elif current.weekday() >= 5:
            dt = "weekend"
        else:
            dt = "weekday"

        # 确定价格（优先级：自定义日期 > 日期类型 > 基础价格）
        if current in custom_date_rules:
            price = custom_date_rules[current]
        elif dt in date_type_rules:
            price = date_type_rules[dt]
        else:
            price = product.base_price

        # 库存信息
        inv = inventory_map.get(current)
        available = inv.available if inv else 0
        inv_status = inv.status if inv else "closed"

        calendar.append({
            "date": current,
            "date_type": dt,
            "price": price,
            "available": available,
            "status": inv_status,
        })

        current += timedelta(days=1)

    return calendar
