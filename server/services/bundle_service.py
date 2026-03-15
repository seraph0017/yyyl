"""
搭配售卖服务

- get_product_bundles：获取商品搭配推荐列表（C端）
- create_bundle_config：创建搭配组合
- update_bundle_config：更新搭配组合
- delete_bundle_config：删除搭配组合
- list_bundle_configs：列表查询
- get_bundle_stats：搭配统计
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.bundle import BundleConfig, BundleItem
from models.order import Order, OrderItem
from models.product import Inventory, Product

logger = logging.getLogger(__name__)

# 排序字段白名单
ALLOWED_SORT_FIELDS = {"id", "sort_order", "created_at", "name"}


async def get_product_bundles(
    db: AsyncSession,
    product_id: int,
    site_id: int = 1,
) -> List[Dict[str, Any]]:
    """获取商品的搭配推荐列表（C端）

    筛选条件：状态为 active、在有效期内、搭配商品有库存

    Args:
        db: 数据库会话
        product_id: 主商品ID
        site_id: 营地ID

    Returns:
        搭配推荐列表
    """
    now = datetime.now(timezone.utc)

    query = (
        select(BundleConfig)
        .options(selectinload(BundleConfig.items).selectinload(BundleItem.product))
        .where(
            BundleConfig.main_product_id == product_id,
            BundleConfig.site_id == site_id,
            BundleConfig.is_deleted.is_(False),
            BundleConfig.status == "active",
        )
    )

    result = await db.execute(query)
    configs = list(result.scalars().unique().all())

    recommend_items: List[Dict[str, Any]] = []

    for config in configs:
        # 检查有效期
        if config.start_at and now < config.start_at:
            continue
        if config.end_at and now > config.end_at:
            continue

        for item in config.items:
            if item.is_deleted:
                continue

            product = item.product
            if not product or product.is_deleted or product.status != "on_sale":
                continue

            # 获取商品首图
            product_image = None
            if product.images and len(product.images) > 0:
                first_img = product.images[0]
                product_image = first_img.get("url") if isinstance(first_img, dict) else first_img

            recommend_items.append({
                "product_id": product.id,
                "product_name": product.name,
                "product_image": product_image,
                "original_price": product.base_price,
                "bundle_price": item.bundle_price,
                "max_quantity": item.max_quantity,
                "is_default_checked": item.is_default_checked,
            })

    return recommend_items


async def create_bundle_config(
    db: AsyncSession,
    data: Dict[str, Any],
    site_id: int = 1,
) -> BundleConfig:
    """创建搭配组合

    Args:
        db: 数据库会话
        data: 搭配组合数据
        site_id: 营地ID

    Returns:
        创建的 BundleConfig 实例
    """
    items_data = data.pop("items", [])

    # 校验主商品存在
    main_product_id = data.get("main_product_id")
    product_result = await db.execute(
        select(Product).where(
            Product.id == main_product_id,
            Product.is_deleted.is_(False),
        )
    )
    if product_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": f"主商品不存在: id={main_product_id}"},
        )

    # 校验搭配商品存在
    item_product_ids = [item["product_id"] for item in items_data]
    products_result = await db.execute(
        select(Product.id).where(
            Product.id.in_(item_product_ids),
            Product.is_deleted.is_(False),
        )
    )
    valid_product_ids = set(products_result.scalars().all())
    for pid in item_product_ids:
        if pid not in valid_product_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 40401, "message": f"搭配商品不存在: id={pid}"},
            )

    # 创建配置
    config = BundleConfig(site_id=site_id, **data)
    db.add(config)
    await db.flush()

    # 创建搭配项
    for item_data in items_data:
        item = BundleItem(
            bundle_config_id=config.id,
            site_id=site_id,
            **item_data,
        )
        db.add(item)

    await db.flush()
    logger.info(f"[搭配] 创建组合: config_id={config.id}, name={config.name}")
    return config


async def update_bundle_config(
    db: AsyncSession,
    config_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> BundleConfig:
    """更新搭配组合

    Args:
        db: 数据库会话
        config_id: 配置ID
        data: 更新数据
        site_id: 营地ID

    Returns:
        更新后的 BundleConfig 实例
    """
    result = await db.execute(
        select(BundleConfig)
        .options(selectinload(BundleConfig.items))
        .where(
            BundleConfig.id == config_id,
            BundleConfig.site_id == site_id,
            BundleConfig.is_deleted.is_(False),
        )
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "搭配组合不存在"},
        )

    items_data = data.pop("items", None)

    # 更新主体字段
    for key, value in data.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)

    # 如果传入了 items，全量替换
    if items_data is not None:
        # 软删除旧的搭配项
        for old_item in config.items:
            old_item.is_deleted = True

        # 创建新搭配项
        for item_data in items_data:
            item = BundleItem(
                bundle_config_id=config.id,
                site_id=site_id,
                **item_data,
            )
            db.add(item)

    await db.flush()
    logger.info(f"[搭配] 更新组合: config_id={config_id}")
    return config


async def delete_bundle_config(
    db: AsyncSession,
    config_id: int,
    site_id: int = 1,
) -> None:
    """删除搭配组合（软删除）

    Args:
        db: 数据库会话
        config_id: 配置ID
        site_id: 营地ID
    """
    result = await db.execute(
        select(BundleConfig)
        .options(selectinload(BundleConfig.items))
        .where(
            BundleConfig.id == config_id,
            BundleConfig.site_id == site_id,
            BundleConfig.is_deleted.is_(False),
        )
    )
    config = result.scalar_one_or_none()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "搭配组合不存在"},
        )

    config.is_deleted = True
    for item in config.items:
        item.is_deleted = True

    await db.flush()
    logger.info(f"[搭配] 删除组合: config_id={config_id}")


async def list_bundle_configs(
    db: AsyncSession,
    site_id: int = 1,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[BundleConfig], int]:
    """搭配组合列表查询

    Args:
        db: 数据库会话
        site_id: 营地ID
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        (配置列表, 总数)
    """
    query = (
        select(BundleConfig)
        .options(selectinload(BundleConfig.items))
        .where(
            BundleConfig.site_id == site_id,
            BundleConfig.is_deleted.is_(False),
        )
    )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(BundleConfig, sort_by)
        query = query.order_by(
            order_col.desc() if sort_order == "desc" else order_col.asc()
        )
    else:
        query = query.order_by(BundleConfig.sort_order.asc(), BundleConfig.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    configs = list(result.scalars().unique().all())

    return configs, total


async def get_bundle_stats(
    db: AsyncSession,
    site_id: int = 1,
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
) -> Dict[str, Any]:
    """搭配统计

    Args:
        db: 数据库会话
        site_id: 营地ID
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        搭配统计数据
    """
    # 搭配订单（is_bundle_item=True 的订单项所关联的订单）
    bundle_order_query = (
        select(func.count(func.distinct(OrderItem.order_id)))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.is_bundle_item.is_(True),
            OrderItem.refund_status == "none",
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
        )
    )

    total_order_query = (
        select(func.count())
        .select_from(Order)
        .where(
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
        )
    )

    bundle_revenue_query = (
        select(func.coalesce(func.sum(OrderItem.actual_price), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.is_bundle_item.is_(True),
            OrderItem.refund_status == "none",
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
        )
    )

    if start_date:
        bundle_order_query = bundle_order_query.where(
            func.date(Order.created_at) >= start_date
        )
        total_order_query = total_order_query.where(
            func.date(Order.created_at) >= start_date
        )
        bundle_revenue_query = bundle_revenue_query.where(
            func.date(Order.created_at) >= start_date
        )
    if end_date:
        bundle_order_query = bundle_order_query.where(
            func.date(Order.created_at) <= end_date
        )
        total_order_query = total_order_query.where(
            func.date(Order.created_at) <= end_date
        )
        bundle_revenue_query = bundle_revenue_query.where(
            func.date(Order.created_at) <= end_date
        )

    total_bundle_orders = (await db.execute(bundle_order_query)).scalar() or 0
    total_orders = (await db.execute(total_order_query)).scalar() or 0
    bundle_revenue = (await db.execute(bundle_revenue_query)).scalar() or Decimal("0")

    bundle_rate = Decimal("0")
    if total_orders > 0:
        bundle_rate = round(Decimal(total_bundle_orders) / Decimal(total_orders) * 100, 2)

    # TOP 搭配组合
    top_query = (
        select(
            OrderItem.bundle_config_id,
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
            func.coalesce(func.sum(OrderItem.actual_price), 0).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.is_bundle_item.is_(True),
            OrderItem.bundle_config_id.isnot(None),
            OrderItem.refund_status == "none",
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
            Order.payment_status == "paid",
        )
        .group_by(OrderItem.bundle_config_id)
        .order_by(func.sum(OrderItem.actual_price).desc())
        .limit(10)
    )

    if start_date:
        top_query = top_query.where(func.date(Order.created_at) >= start_date)
    if end_date:
        top_query = top_query.where(func.date(Order.created_at) <= end_date)

    top_result = await db.execute(top_query)
    top_rows = top_result.all()

    # 查询搭配组合名称
    top_bundles = []
    if top_rows:
        config_ids = [row.bundle_config_id for row in top_rows if row.bundle_config_id]
        configs_result = await db.execute(
            select(BundleConfig.id, BundleConfig.name).where(
                BundleConfig.id.in_(config_ids)
            )
        )
        config_name_map = {r.id: r.name for r in configs_result.all()}

        for row in top_rows:
            top_bundles.append({
                "bundle_config_id": row.bundle_config_id,
                "bundle_name": config_name_map.get(row.bundle_config_id, ""),
                "order_count": row.order_count,
                "revenue": row.revenue,
            })

    return {
        "total_bundle_orders": total_bundle_orders,
        "bundle_rate": bundle_rate,
        "bundle_revenue": bundle_revenue,
        "top_bundles": top_bundles,
    }
