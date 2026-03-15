"""
营地地图 & 小游戏相关 Schemas

- CampMapCreate / CampMapUpdate / CampMapResponse：营地地图
- CampMapZoneCreate / CampMapZoneUpdate / CampMapZoneResponse：地图区域
- MiniGameCreate / MiniGameUpdate / MiniGameResponse：H5小游戏
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 地图区域 ----

class CampMapZoneCreate(BaseModel):
    """创建地图区域"""

    model_config = ConfigDict(populate_by_name=True)

    zone_name: str = Field(min_length=1, max_length=50, description="区域名称")
    zone_code: Optional[str] = Field(
        default=None, max_length=20, description="区域编码",
    )
    coordinates: List[Dict[str, Any]] = Field(
        min_length=1, description="多边形坐标点 [{x, y}]",
    )
    product_ids: List[int] = Field(
        default_factory=list, description="关联商品ID列表",
    )
    description: Optional[str] = Field(default=None, description="区域描述")
    sort_order: int = Field(default=0, ge=0, description="排序")


class CampMapZoneUpdate(BaseModel):
    """更新地图区域（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    zone_name: Optional[str] = Field(
        default=None, max_length=50, description="区域名称",
    )
    zone_code: Optional[str] = Field(
        default=None, max_length=20, description="区域编码",
    )
    coordinates: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="多边形坐标点",
    )
    product_ids: Optional[List[int]] = Field(
        default=None, description="关联商品ID列表",
    )
    description: Optional[str] = Field(default=None, description="区域描述")
    sort_order: Optional[int] = Field(default=None, ge=0, description="排序")


class CampMapZoneResponse(BaseModel):
    """地图区域响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="区域ID")
    camp_map_id: int = Field(description="营地地图ID")
    zone_name: str = Field(description="区域名称")
    zone_code: Optional[str] = Field(default=None, description="区域编码")
    coordinates: List[Dict[str, Any]] = Field(
        default_factory=list, description="多边形坐标点",
    )
    product_ids: List[int] = Field(
        default_factory=list, description="关联商品ID列表",
    )
    description: Optional[str] = Field(default=None, description="区域描述")
    sort_order: int = Field(default=0, description="排序")


# ---- 营地地图 ----

class CampMapCreate(BaseModel):
    """创建营地地图"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=100, description="地图名称")
    map_image: str = Field(min_length=1, max_length=500, description="底图URL")
    map_type: str = Field(default="image", description="地图类型: svg/image")
    site_id: int = Field(default=1, description="营地ID")

    @field_validator("map_type")
    @classmethod
    def validate_map_type(cls, v: str) -> str:
        if v not in ("svg", "image"):
            raise ValueError("地图类型必须为 svg 或 image")
        return v


class CampMapUpdate(BaseModel):
    """更新营地地图（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=100, description="地图名称")
    map_image: Optional[str] = Field(
        default=None, max_length=500, description="底图URL",
    )
    map_type: Optional[str] = Field(default=None, description="地图类型: svg/image")
    status: Optional[str] = Field(default=None, description="状态: active/inactive")

    @field_validator("map_type")
    @classmethod
    def validate_map_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("svg", "image"):
            raise ValueError("地图类型必须为 svg 或 image")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "inactive"):
            raise ValueError("状态必须为 active 或 inactive")
        return v


class CampMapResponse(BaseModel):
    """营地地图响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="地图ID")
    site_id: int = Field(description="营地ID")
    name: str = Field(description="地图名称")
    map_image: str = Field(description="底图URL")
    map_type: str = Field(description="地图类型: svg/image")
    status: str = Field(description="状态: active/inactive")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    # 关联
    zones: List[CampMapZoneResponse] = Field(
        default_factory=list, description="地图区域列表",
    )


# ---- H5小游戏 ----

class MiniGameCreate(BaseModel):
    """创建H5小游戏"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=100, description="游戏名称")
    game_url: str = Field(min_length=1, max_length=500, description="H5游戏URL")
    cover_image: Optional[str] = Field(
        default=None, max_length=500, description="封面图URL",
    )
    description: Optional[str] = Field(default=None, description="游戏描述")
    sort_order: int = Field(default=0, ge=0, description="排序")
    site_id: int = Field(default=1, description="营地ID")


class MiniGameUpdate(BaseModel):
    """更新H5小游戏（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=100, description="游戏名称")
    game_url: Optional[str] = Field(
        default=None, max_length=500, description="H5游戏URL",
    )
    cover_image: Optional[str] = Field(
        default=None, max_length=500, description="封面图URL",
    )
    description: Optional[str] = Field(default=None, description="游戏描述")
    status: Optional[str] = Field(default=None, description="状态: active/inactive")
    sort_order: Optional[int] = Field(default=None, ge=0, description="排序")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "inactive"):
            raise ValueError("状态必须为 active 或 inactive")
        return v


class MiniGameResponse(BaseModel):
    """H5小游戏响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="游戏ID")
    name: str = Field(description="游戏名称")
    cover_image: Optional[str] = Field(default=None, description="封面图URL")
    game_url: str = Field(description="H5游戏URL")
    description: Optional[str] = Field(default=None, description="游戏描述")
    status: str = Field(description="状态: active/inactive")
    sort_order: int = Field(default=0, description="排序")
    site_id: int = Field(description="营地ID")
    points_reward: Optional[int] = Field(default=None, description="积分奖励")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
