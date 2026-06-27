"""
营地地图服务

- CRUD for CampMap
- CRUD for CampMapZone
- get_zone_availability：获取区域营位可用状态
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.camp_map import CampMap, CampMapZone, PageViewStat
from models.product import Inventory, Product
from schemas.camp_map import normalize_camp_map_zone_coordinates

logger = logging.getLogger(__name__)

# 排序字段白名单
ALLOWED_MAP_SORT_FIELDS = {"id", "name", "created_at"}
ALLOWED_ZONE_SORT_FIELDS = {"id", "zone_name", "sort_order"}


# ---- 营地地图 CRUD ----

async def create_camp_map(
    db: AsyncSession,
    data: Dict[str, Any],
    site_id: int = 1,
) -> CampMap:
    """创建营地地图

    Args:
        db: 数据库会话
        data: 地图数据
        site_id: 营地ID

    Returns:
        创建的 CampMap 实例
    """
    camp_map = CampMap(site_id=site_id, **data)
    db.add(camp_map)
    await db.flush()

    logger.info(f"[地图] 创建: id={camp_map.id}, name={camp_map.name}")
    return camp_map


async def update_camp_map(
    db: AsyncSession,
    map_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> CampMap:
    """更新营地地图

    Args:
        db: 数据库会话
        map_id: 地图ID
        data: 更新数据
        site_id: 营地ID

    Returns:
        更新后的 CampMap 实例
    """
    result = await db.execute(
        select(CampMap)
        .options(selectinload(CampMap.zones))
        .where(
            CampMap.id == map_id,
            CampMap.site_id == site_id,
            CampMap.is_deleted.is_(False),
        )
    )
    camp_map = result.scalar_one_or_none()

    if camp_map is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "营地地图不存在"},
        )

    for key, value in data.items():
        if hasattr(camp_map, key) and value is not None:
            setattr(camp_map, key, value)

    await db.flush()
    logger.info(f"[地图] 更新: id={map_id}")
    return camp_map


async def delete_camp_map(
    db: AsyncSession,
    map_id: int,
    site_id: int = 1,
) -> None:
    """删除营地地图（软删除）

    Args:
        db: 数据库会话
        map_id: 地图ID
        site_id: 营地ID
    """
    result = await db.execute(
        select(CampMap)
        .options(selectinload(CampMap.zones))
        .where(
            CampMap.id == map_id,
            CampMap.site_id == site_id,
            CampMap.is_deleted.is_(False),
        )
    )
    camp_map = result.scalar_one_or_none()

    if camp_map is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "营地地图不存在"},
        )

    camp_map.is_deleted = True
    for zone in camp_map.zones:
        zone.is_deleted = True

    await db.flush()
    logger.info(f"[地图] 删除: id={map_id}")


async def get_camp_map(
    db: AsyncSession,
    map_id: int,
    site_id: int = 1,
) -> CampMap:
    """获取营地地图详情

    Args:
        db: 数据库会话
        map_id: 地图ID
        site_id: 营地ID

    Returns:
        CampMap 实例
    """
    result = await db.execute(
        select(CampMap)
        .options(selectinload(CampMap.zones))
        .where(
            CampMap.id == map_id,
            CampMap.site_id == site_id,
            CampMap.is_deleted.is_(False),
        )
    )
    camp_map = result.scalar_one_or_none()

    if camp_map is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "营地地图不存在"},
        )

    return camp_map


async def list_camp_maps(
    db: AsyncSession,
    site_id: int = 1,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[CampMap], int]:
    """营地地图列表查询

    Args:
        db: 数据库会话
        site_id: 营地ID
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        (地图列表, 总数)
    """
    query = (
        select(CampMap)
        .options(selectinload(CampMap.zones))
        .where(
            CampMap.site_id == site_id,
            CampMap.is_deleted.is_(False),
        )
    )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_MAP_SORT_FIELDS:
        order_col = getattr(CampMap, sort_by)
        query = query.order_by(
            order_col.desc() if sort_order == "desc" else order_col.asc()
        )
    else:
        query = query.order_by(CampMap.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    maps = list(result.scalars().unique().all())

    return maps, total


# ---- 地图区域 CRUD ----

async def create_camp_map_zone(
    db: AsyncSession,
    map_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> CampMapZone:
    """创建地图区域

    Args:
        db: 数据库会话
        map_id: 地图ID
        data: 区域数据
        site_id: 营地ID

    Returns:
        创建的 CampMapZone 实例
    """
    # 校验地图存在
    map_result = await db.execute(
        select(CampMap).where(
            CampMap.id == map_id,
            CampMap.site_id == site_id,
            CampMap.is_deleted.is_(False),
        )
    )
    if map_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "营地地图不存在"},
        )

    zone = CampMapZone(camp_map_id=map_id, **data)
    db.add(zone)
    await db.flush()

    logger.info(f"[地图] 创建区域: id={zone.id}, map_id={map_id}")
    return zone


async def update_camp_map_zone(
    db: AsyncSession,
    zone_id: int,
    data: Dict[str, Any],
    site_id: int = 1,
) -> CampMapZone:
    """更新地图区域

    Args:
        db: 数据库会话
        zone_id: 区域ID
        data: 更新数据
        site_id: 营地ID

    Returns:
        更新后的 CampMapZone 实例
    """
    result = await db.execute(
        select(CampMapZone)
        .join(CampMap, CampMap.id == CampMapZone.camp_map_id)
        .where(
            CampMapZone.id == zone_id,
            CampMap.site_id == site_id,
            CampMapZone.is_deleted.is_(False),
        )
    )
    zone = result.scalar_one_or_none()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "地图区域不存在"},
        )

    nullable_fields = {"link_type", "link_target", "link_label", "description", "zone_code"}
    for key, value in data.items():
        if hasattr(zone, key) and (value is not None or key in nullable_fields):
            setattr(zone, key, value)

    await db.flush()
    logger.info(f"[地图] 更新区域: id={zone_id}")
    return zone


async def delete_camp_map_zone(
    db: AsyncSession,
    zone_id: int,
    site_id: int = 1,
) -> None:
    """删除地图区域（软删除）

    Args:
        db: 数据库会话
        zone_id: 区域ID
        site_id: 营地ID
    """
    result = await db.execute(
        select(CampMapZone)
        .join(CampMap, CampMap.id == CampMapZone.camp_map_id)
        .where(
            CampMapZone.id == zone_id,
            CampMap.site_id == site_id,
            CampMapZone.is_deleted.is_(False),
        )
    )
    zone = result.scalar_one_or_none()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "地图区域不存在"},
        )

    zone.is_deleted = True
    await db.flush()
    logger.info(f"[地图] 删除区域: id={zone_id}")


# ---- 区域可用状态 ----

async def get_zone_availability(
    db: AsyncSession,
    camp_map_id: int,
    target_date: date,
    site_id: int = 1,
) -> List[Dict[str, Any]]:
    """获取区域营位可用状态

    查询地图下所有区域，并按区域关联的商品聚合库存信息。

    Args:
        db: 数据库会话
        camp_map_id: 地图ID
        target_date: 查询日期
        site_id: 营地ID

    Returns:
        区域可用状态列表
    """
    # 查询地图和区域
    map_result = await db.execute(
        select(CampMap)
        .options(selectinload(CampMap.zones))
        .where(
            CampMap.id == camp_map_id,
            CampMap.site_id == site_id,
            CampMap.is_deleted.is_(False),
        )
    )
    camp_map = map_result.scalar_one_or_none()

    if camp_map is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "营地地图不存在"},
        )

    # 收集所有相关商品ID
    all_product_ids = set()
    for zone in camp_map.zones:
        if not zone.is_deleted and zone.product_ids:
            all_product_ids.update(zone.product_ids)

    # 批量查询库存
    inventory_map: Dict[int, Dict[str, Any]] = {}
    if all_product_ids:
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id.in_(list(all_product_ids)),
                Inventory.site_id == site_id,
                Inventory.date == target_date,
                Inventory.is_deleted.is_(False),
            )
        )
        for inv in inv_result.scalars().all():
            inventory_map[inv.product_id] = {
                "total": inv.total,
                "available": inv.available,
                "locked": inv.locked,
                "sold": inv.sold,
                "status": inv.status,
            }

    # 构建区域可用状态
    zone_statuses = []
    for zone in camp_map.zones:
        if zone.is_deleted:
            continue

        # 聚合区域内商品的库存
        zone_total = 0
        zone_available = 0
        zone_sold = 0

        for pid in (zone.product_ids or []):
            inv_info = inventory_map.get(pid)
            if inv_info:
                zone_total += inv_info["total"]
                zone_available += inv_info["available"]
                zone_sold += inv_info["sold"]

        # 判断可用状态
        if zone_total == 0:
            availability = "closed"
        elif zone_available == 0:
            availability = "sold_out"
        elif zone_available <= zone_total * 0.2:
            availability = "low"
        else:
            availability = "available"

        zone_statuses.append({
            "zone_id": zone.id,
            "id": zone.id,
            "zone_name": zone.zone_name,
            "zone_code": zone.zone_code,
            "coordinates": normalize_camp_map_zone_coordinates(zone.coordinates),
            "product_ids": zone.product_ids,
            "description": zone.description,
            "sort_order": zone.sort_order,
            "link_type": zone.link_type,
            "link_target": zone.link_target,
            "link_label": zone.link_label,
            "click_count": zone.click_count,
            "total": zone_total,
            "total_count": zone_total,
            "available": zone_available,
            "available_count": zone_available,
            "sold": zone_sold,
            "availability": availability,
        })

    return zone_statuses


async def record_zone_click(
    db: AsyncSession,
    *,
    zone_id: int,
    site_id: int = 1,
) -> Dict[str, Any]:
    """记录地图热区点击，按营地隔离。"""
    update_result = await db.execute(
        update(CampMapZone)
        .where(
            CampMapZone.id == zone_id,
            CampMapZone.is_deleted.is_(False),
            CampMapZone.camp_map_id.in_(
                select(CampMap.id).where(
                    CampMap.site_id == site_id,
                    CampMap.is_deleted.is_(False),
                )
            ),
        )
        .values(click_count=CampMapZone.click_count + 1)
        .returning(
            CampMapZone.id,
            CampMapZone.click_count,
            CampMapZone.link_type,
            CampMapZone.link_target,
            CampMapZone.link_label,
        )
    )
    row = update_result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "地图区域不存在"},
        )

    await db.flush()
    return {
        "zone_id": row.id,
        "click_count": row.click_count,
        "link_type": row.link_type,
        "link_target": row.link_target,
        "link_label": row.link_label,
    }


async def _record_zone_click_legacy(
    db: AsyncSession,
    *,
    zone_id: int,
    site_id: int = 1,
) -> Dict[str, Any]:
    """测试替身数据库不支持 SQLAlchemy Row 返回时的兼容路径。"""
    result = await db.execute(
        select(CampMapZone)
        .join(CampMap, CampMap.id == CampMapZone.camp_map_id)
        .where(
            CampMapZone.id == zone_id,
            CampMap.site_id == site_id,
            CampMapZone.is_deleted.is_(False),
            CampMap.is_deleted.is_(False),
        )
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "地图区域不存在"},
        )

    zone.click_count = (zone.click_count or 0) + 1
    await db.flush()
    return {
        "zone_id": zone.id,
        "click_count": zone.click_count,
        "link_type": zone.link_type,
        "link_target": zone.link_target,
        "link_label": zone.link_label,
    }


async def record_page_view(
    db: AsyncSession,
    *,
    site_id: int,
    page_key: str,
    page_title: Optional[str] = None,
    user_id: Optional[int] = None,
    stat_date: Optional[date] = None,
) -> PageViewStat:
    """记录页面浏览量，按营地、页面和自然日聚合。"""
    stat_date = stat_date or date.today()
    now = datetime.now(timezone.utc)
    stmt = pg_insert(PageViewStat).values(
        site_id=site_id,
        page_key=page_key,
        page_title=page_title,
        stat_date=stat_date,
        view_count=1,
        user_count=1 if user_id is not None else 0,
        last_viewed_at=now,
        is_deleted=False,
    )
    update_values = {
        "view_count": PageViewStat.view_count + 1,
        "user_count": PageViewStat.user_count + (1 if user_id is not None else 0),
        "last_viewed_at": now,
        "is_deleted": False,
    }
    if page_title:
        update_values["page_title"] = page_title

    result = await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[
                PageViewStat.site_id,
                PageViewStat.page_key,
                PageViewStat.stat_date,
            ],
            set_=update_values,
        ).returning(PageViewStat)
    )
    stat = result.scalar_one()
    await db.flush()
    return stat


async def list_page_view_stats(
    db: AsyncSession,
    *,
    site_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page_key: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[PageViewStat], int]:
    """查询页面浏览统计。"""
    conditions = [
        PageViewStat.site_id == site_id,
        PageViewStat.is_deleted.is_(False),
    ]
    if start_date:
        conditions.append(PageViewStat.stat_date >= start_date)
    if end_date:
        conditions.append(PageViewStat.stat_date <= end_date)
    if page_key:
        conditions.append(PageViewStat.page_key == page_key)

    query = select(PageViewStat).where(*conditions)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(PageViewStat.stat_date.desc(), PageViewStat.view_count.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def summarize_page_view_stats(
    db: AsyncSession,
    *,
    site_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page_key: Optional[str] = None,
) -> Dict[str, int]:
    """查询页面浏览统计摘要，按完整筛选条件聚合而不是按分页结果汇总。"""
    conditions = [
        PageViewStat.site_id == site_id,
        PageViewStat.is_deleted.is_(False),
    ]
    if start_date:
        conditions.append(PageViewStat.stat_date >= start_date)
    if end_date:
        conditions.append(PageViewStat.stat_date <= end_date)
    if page_key:
        conditions.append(PageViewStat.page_key == page_key)

    result = await db.execute(
        select(
            func.count(PageViewStat.id),
            func.coalesce(func.sum(PageViewStat.view_count), 0),
            func.coalesce(func.sum(PageViewStat.user_count), 0),
        ).where(*conditions)
    )
    record_count, view_count, user_count = result.all()[0]
    return {
        "record_count": int(record_count or 0),
        "view_count": int(view_count or 0),
        "user_count": int(user_count or 0),
    }
