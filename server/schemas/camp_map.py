"""
营地地图 & 小游戏相关 Schemas

- CampMapCreate / CampMapUpdate / CampMapResponse：营地地图
- CampMapZoneCreate / CampMapZoneUpdate / CampMapZoneResponse：地图区域
- MiniGameCreate / MiniGameUpdate / MiniGameResponse：H5小游戏
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_camp_map_zone_coordinates(value: Any) -> Dict[str, float]:
    """兼容旧版多边形坐标，统一归一为矩形热区百分比。"""
    if isinstance(value, CampMapZoneRect):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        points = []
        for point in value:
            if isinstance(point, dict) and "x" in point and "y" in point:
                points.append((float(point["x"]), float(point["y"])))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                points.append((float(point[0]), float(point[1])))

        if not points:
            return {"x": 0, "y": 0, "width": 1, "height": 1}

        xs = [min(max(x, 0), 100) for x, _ in points]
        ys = [min(max(y, 0), 100) for _, y in points]
        x = min(xs)
        y = min(ys)
        width = max(max(xs) - x, 1)
        height = max(max(ys) - y, 1)
        return {
            "x": x,
            "y": y,
            "width": min(width, 100 - x),
            "height": min(height, 100 - y),
        }
    return value


# ---- 地图区域 ----

class CampMapZoneRect(BaseModel):
    """地图热区矩形坐标，单位为底图百分比"""

    x: float = Field(ge=0, le=100, description="左侧百分比")
    y: float = Field(ge=0, le=100, description="顶部百分比")
    width: float = Field(gt=0, le=100, description="宽度百分比")
    height: float = Field(gt=0, le=100, description="高度百分比")

    @model_validator(mode="after")
    def validate_bounds(self) -> "CampMapZoneRect":
        if self.x + self.width > 100:
            raise ValueError("热区宽度不能超出底图")
        if self.y + self.height > 100:
            raise ValueError("热区高度不能超出底图")
        return self


class CampMapZoneCreate(BaseModel):
    """创建地图区域"""

    model_config = ConfigDict(populate_by_name=True)

    zone_name: str = Field(min_length=1, max_length=50, description="区域名称")
    zone_code: Optional[str] = Field(
        default=None, max_length=20, description="区域编码",
    )
    coordinates: CampMapZoneRect = Field(
        description="矩形热区坐标 {x,y,width,height}，单位为百分比",
    )
    product_ids: List[int] = Field(
        default_factory=list, description="关联商品ID列表",
    )
    description: Optional[str] = Field(default=None, description="区域描述")
    sort_order: int = Field(default=0, ge=0, description="排序")
    link_type: Optional[str] = Field(
        default=None, description="热区链接类型: product/cms/h5/none",
    )
    link_target: Optional[str] = Field(
        default=None, max_length=500, description="热区链接目标",
    )
    link_label: Optional[str] = Field(
        default=None, max_length=50, description="热区链接按钮文案",
    )

    @field_validator("link_type")
    @classmethod
    def validate_link_type(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, "", "none"):
            return None
        if v not in ("product", "cms", "h5"):
            raise ValueError("热区链接类型必须为 product/cms/h5/none")
        return v

    @field_validator("coordinates", mode="before")
    @classmethod
    def validate_coordinates(cls, v: Any) -> Any:
        return normalize_camp_map_zone_coordinates(v)


class CampMapZoneUpdate(BaseModel):
    """更新地图区域（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    zone_name: Optional[str] = Field(
        default=None, max_length=50, description="区域名称",
    )
    zone_code: Optional[str] = Field(
        default=None, max_length=20, description="区域编码",
    )
    coordinates: Optional[CampMapZoneRect] = Field(
        default=None, description="矩形热区坐标 {x,y,width,height}，单位为百分比",
    )
    product_ids: Optional[List[int]] = Field(
        default=None, description="关联商品ID列表",
    )
    description: Optional[str] = Field(default=None, description="区域描述")
    sort_order: Optional[int] = Field(default=None, ge=0, description="排序")
    link_type: Optional[str] = Field(
        default=None, description="热区链接类型: product/cms/h5/none",
    )
    link_target: Optional[str] = Field(
        default=None, max_length=500, description="热区链接目标",
    )
    link_label: Optional[str] = Field(
        default=None, max_length=50, description="热区链接按钮文案",
    )

    @field_validator("link_type")
    @classmethod
    def validate_link_type(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, "", "none"):
            return None
        if v not in ("product", "cms", "h5"):
            raise ValueError("热区链接类型必须为 product/cms/h5/none")
        return v

    @field_validator("coordinates", mode="before")
    @classmethod
    def validate_coordinates(cls, v: Any) -> Any:
        if v is None:
            return v
        return normalize_camp_map_zone_coordinates(v)


class CampMapZoneResponse(BaseModel):
    """地图区域响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="区域ID")
    camp_map_id: int = Field(description="营地地图ID")
    zone_name: str = Field(description="区域名称")
    zone_code: Optional[str] = Field(default=None, description="区域编码")
    coordinates: CampMapZoneRect = Field(
        description="矩形热区坐标 {x,y,width,height}，单位为百分比",
    )
    product_ids: List[int] = Field(
        default_factory=list, description="关联商品ID列表",
    )
    description: Optional[str] = Field(default=None, description="区域描述")
    sort_order: int = Field(default=0, description="排序")
    link_type: Optional[str] = Field(default=None, description="热区链接类型")
    link_target: Optional[str] = Field(default=None, description="热区链接目标")
    link_label: Optional[str] = Field(default=None, description="热区链接按钮文案")
    click_count: int = Field(default=0, description="热区点击次数")

    @field_validator("coordinates", mode="before")
    @classmethod
    def validate_coordinates(cls, v: Any) -> Any:
        return normalize_camp_map_zone_coordinates(v)


class PageViewTrackRequest(BaseModel):
    """页面浏览埋点请求"""

    page_key: str = Field(min_length=1, max_length=100, description="页面标识")
    page_title: Optional[str] = Field(default=None, max_length=100, description="页面标题")


class PageViewStatResponse(BaseModel):
    """页面浏览统计响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="统计ID")
    site_id: int = Field(description="营地ID")
    page_key: str = Field(description="页面标识")
    page_title: Optional[str] = Field(default=None, description="页面标题")
    stat_date: Any = Field(description="统计日期")
    view_count: int = Field(description="浏览次数")
    user_count: int = Field(description="登录用户访问次数")
    last_viewed_at: Optional[datetime] = Field(default=None, description="最近访问时间")


# ---- 营地地图 ----

class CampMapCreate(BaseModel):
    """创建营地地图"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=100, description="地图名称")
    map_image: str = Field(min_length=1, max_length=500, description="底图URL")
    map_type: str = Field(default="image", description="地图类型: image/svg")
    site_id: int = Field(default=1, description="营地ID")

    @field_validator("map_type")
    @classmethod
    def validate_map_type(cls, v: str) -> str:
        if v not in ("svg", "image"):
            raise ValueError("地图类型必须为 image 或 svg")
        return v


class CampMapUpdate(BaseModel):
    """更新营地地图（所有字段可选）"""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=100, description="地图名称")
    map_image: Optional[str] = Field(
        default=None, max_length=500, description="底图URL",
    )
    map_type: Optional[str] = Field(default=None, description="地图类型: image/svg")
    status: Optional[str] = Field(default=None, description="状态: active/inactive")

    @field_validator("map_type")
    @classmethod
    def validate_map_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("svg", "image"):
            raise ValueError("地图类型必须为 image 或 svg")
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
    map_type: str = Field(description="地图类型: image/svg")
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
