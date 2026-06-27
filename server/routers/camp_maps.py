"""
营地地图 + 小游戏路由

C端：
- GET  /api/v1/camp-maps                         — 获取营地地图列表（🌐 游客可访问）
- GET  /api/v1/camp-maps/{map_id}/zones          — 获取地图区域及可用状态（🌐）
- GET  /api/v1/games                             — 游戏列表（🌐）
- GET  /api/v1/games/{game_id}/token             — 获取游戏签名token（👤 用户）

B端：
- GET/POST       /api/v1/admin/camp-maps          — 地图列表/创建
- PUT/DELETE     /api/v1/admin/camp-maps/{map_id} — 地图更新/删除
- POST           /api/v1/admin/camp-maps/{map_id}/zones — 添加区域
- PUT/DELETE     /api/v1/admin/camp-maps/zones/{zone_id} — 区域更新/删除
- GET/POST       /api/v1/admin/games              — 游戏列表/创建
- PUT/DELETE     /api/v1/admin/games/{game_id}    — 游戏更新/删除
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from middleware.auth import get_current_admin, get_current_user, get_optional_user
from middleware.site import get_site_id
from models.admin import AdminUser
from models.user import User
from schemas.camp_map import (
    CampMapCreate,
    CampMapResponse,
    CampMapUpdate,
    CampMapZoneCreate,
    CampMapZoneResponse,
    CampMapZoneUpdate,
    MiniGameCreate,
    MiniGameResponse,
    MiniGameUpdate,
    PageViewStatResponse,
    PageViewTrackRequest,
)
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from services import camp_map_service, game_service

router = APIRouter(tags=["营地地图"])


# ========== C端接口：地图 ==========


@router.get("/api/v1/camp-maps", summary="营地地图列表")
async def list_camp_maps_public(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端获取营地地图列表（游客可访问）

    只返回 active 状态的地图。
    """
    site_id = get_site_id(request)
    maps, total = await camp_map_service.list_camp_maps(
        db, site_id=site_id, page=1, page_size=100,
    )
    # C端只展示 active 状态
    active_maps = [m for m in maps if m.status == "active"]
    items = [CampMapResponse.model_validate(m) for m in active_maps]
    return ResponseModel.success(data=items)


@router.get("/api/v1/camp-maps/{map_id}/zones", summary="获取地图区域及可用状态")
async def get_map_zones(
    map_id: int,
    request: Request,
    target_date: Optional[date] = Query(
        default=None, description="查询日期（默认今天）",
    ),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端获取地图区域列表及营位可用状态（游客可访问）

    返回每个区域的坐标、总数/可用/已售数量和可用状态标签。
    """
    site_id = get_site_id(request)
    if target_date is None:
        target_date = date.today()

    zones = await camp_map_service.get_zone_availability(
        db,
        camp_map_id=map_id,
        target_date=target_date,
        site_id=site_id,
    )
    return ResponseModel.success(data=zones)


@router.post("/api/v1/camp-maps/zones/{zone_id}/click", summary="记录地图热区点击")
async def record_zone_click(
    zone_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端记录营地地图热区点击，返回热区链接信息。"""
    site_id = get_site_id(request)
    data = await camp_map_service.record_zone_click(
        db,
        zone_id=zone_id,
        site_id=site_id,
    )
    await db.commit()
    return ResponseModel.success(data=data)


@router.post("/api/v1/analytics/page-view", summary="记录页面浏览")
async def record_page_view(
    body: PageViewTrackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端页面浏览量埋点，按营地、页面和自然日聚合。"""
    site_id = get_site_id(request)
    stat = await camp_map_service.record_page_view(
        db,
        site_id=site_id,
        page_key=body.page_key,
        page_title=body.page_title,
        user_id=user.id if user else None,
    )
    await db.commit()
    return ResponseModel.success(data=PageViewStatResponse.model_validate(stat))


# ========== C端接口：游戏 ==========


@router.get("/api/v1/games", summary="游戏列表")
async def list_games_public(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端获取H5小游戏列表（游客可访问）

    只返回 active 状态的游戏。
    """
    site_id = get_site_id(request)
    games, total = await game_service.list_mini_games(
        db, site_id=site_id, game_status="active", page=1, page_size=100,
    )
    items = [MiniGameResponse.model_validate(g) for g in games]
    return ResponseModel.success(data=items)


@router.get("/api/v1/games/{game_id}/token", summary="获取游戏签名token")
async def get_game_token(
    game_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户获取游戏签名 token（HMAC-SHA256）

    token 用于游戏客户端验证用户身份，防作弊。1小时有效。
    """
    site_id = get_site_id(request)
    # 校验游戏存在且有效
    game = await game_service.get_mini_game(db, game_id=game_id, site_id=site_id)
    token_data = game_service.generate_game_token(
        user_id=user.id,
        secret_key=settings.JWT_SECRET_KEY,
    )
    return ResponseModel.success(data=token_data)


# ========== B端接口：地图管理 ==========


@router.get("/api/v1/admin/camp-maps", summary="地图列表（管理）")
async def list_camp_maps_admin(
    request: Request,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """B端地图列表，包含所有状态"""
    site_id = get_site_id(request)
    maps, total = await camp_map_service.list_camp_maps(
        db,
        site_id=site_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [CampMapResponse.model_validate(m) for m in maps]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/api/v1/admin/camp-maps", summary="创建地图")
async def create_camp_map(
    body: CampMapCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建营地地图"""
    site_id = get_site_id(request)
    camp_map = await camp_map_service.create_camp_map(
        db,
        data=body.model_dump(exclude={"site_id"}),
        site_id=site_id,
    )
    await db.commit()
    result = CampMapResponse.model_validate(camp_map)
    return ResponseModel.success(data=result, message="地图创建成功")


@router.put("/api/v1/admin/camp-maps/{map_id}", summary="更新地图")
async def update_camp_map(
    map_id: int,
    body: CampMapUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新营地地图"""
    site_id = get_site_id(request)
    camp_map = await camp_map_service.update_camp_map(
        db,
        map_id=map_id,
        data=body.model_dump(exclude_unset=True),
        site_id=site_id,
    )
    await db.commit()
    result = CampMapResponse.model_validate(camp_map)
    return ResponseModel.success(data=result, message="地图更新成功")


@router.delete("/api/v1/admin/camp-maps/{map_id}", summary="删除地图")
async def delete_camp_map(
    map_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除营地地图（软删除，同时删除关联区域）"""
    site_id = get_site_id(request)
    await camp_map_service.delete_camp_map(
        db, map_id=map_id, site_id=site_id,
    )
    await db.commit()
    return ResponseModel.success(message="地图已删除")


@router.post("/api/v1/admin/camp-maps/{map_id}/zones", summary="添加地图区域")
async def create_camp_map_zone(
    map_id: int,
    body: CampMapZoneCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """为地图添加区域"""
    site_id = get_site_id(request)
    zone = await camp_map_service.create_camp_map_zone(
        db,
        map_id=map_id,
        data=body.model_dump(mode="json"),
        site_id=site_id,
    )
    await db.commit()
    result = CampMapZoneResponse.model_validate(zone)
    return ResponseModel.success(data=result, message="区域添加成功")


@router.put("/api/v1/admin/camp-maps/zones/{zone_id}", summary="更新区域")
async def update_camp_map_zone(
    zone_id: int,
    body: CampMapZoneUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新地图区域"""
    site_id = get_site_id(request)
    zone = await camp_map_service.update_camp_map_zone(
        db,
        zone_id=zone_id,
        data=body.model_dump(exclude_unset=True, mode="json"),
        site_id=site_id,
    )
    await db.commit()
    result = CampMapZoneResponse.model_validate(zone)
    return ResponseModel.success(data=result, message="区域更新成功")


@router.delete("/api/v1/admin/camp-maps/zones/{zone_id}", summary="删除区域")
async def delete_camp_map_zone(
    zone_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除地图区域（软删除）"""
    site_id = get_site_id(request)
    await camp_map_service.delete_camp_map_zone(
        db, zone_id=zone_id, site_id=site_id,
    )
    await db.commit()
    return ResponseModel.success(message="区域已删除")


@router.get("/api/v1/admin/analytics/page-views", summary="页面浏览统计")
async def list_page_view_stats(
    request: Request,
    start_date: Optional[date] = Query(default=None, description="开始日期"),
    end_date: Optional[date] = Query(default=None, description="结束日期"),
    page_key: Optional[str] = Query(default=None, description="页面标识"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """B端查看页面浏览统计。"""
    site_id = get_site_id(request)
    stats, total = await camp_map_service.list_page_view_stats(
        db,
        site_id=site_id,
        start_date=start_date,
        end_date=end_date,
        page_key=page_key,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    summary = await camp_map_service.summarize_page_view_stats(
        db,
        site_id=site_id,
        start_date=start_date,
        end_date=end_date,
        page_key=page_key,
    )
    items = [PageViewStatResponse.model_validate(item) for item in stats]
    response = PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    data = response.model_dump(mode="json")
    data["data"]["summary"] = summary
    return data


# ========== B端接口：游戏管理 ==========


@router.get("/api/v1/admin/games", summary="游戏列表（管理）")
async def list_games_admin(
    request: Request,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """B端游戏列表，包含所有状态"""
    site_id = get_site_id(request)
    games, total = await game_service.list_mini_games(
        db,
        site_id=site_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [MiniGameResponse.model_validate(g) for g in games]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/api/v1/admin/games", summary="创建游戏")
async def create_game(
    body: MiniGameCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建H5小游戏"""
    site_id = get_site_id(request)
    game = await game_service.create_mini_game(
        db,
        data=body.model_dump(exclude={"site_id"}),
        site_id=site_id,
    )
    await db.commit()
    result = MiniGameResponse.model_validate(game)
    return ResponseModel.success(data=result, message="游戏创建成功")


@router.put("/api/v1/admin/games/{game_id}", summary="更新游戏")
async def update_game(
    game_id: int,
    body: MiniGameUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新H5小游戏"""
    site_id = get_site_id(request)
    game = await game_service.update_mini_game(
        db,
        game_id=game_id,
        data=body.model_dump(exclude_unset=True),
        site_id=site_id,
    )
    await db.commit()
    result = MiniGameResponse.model_validate(game)
    return ResponseModel.success(data=result, message="游戏更新成功")


@router.delete("/api/v1/admin/games/{game_id}", summary="删除游戏")
async def delete_game(
    game_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除H5小游戏（软删除）"""
    site_id = get_site_id(request)
    await game_service.delete_mini_game(
        db, game_id=game_id, site_id=site_id,
    )
    await db.commit()
    return ResponseModel.success(message="游戏已删除")
