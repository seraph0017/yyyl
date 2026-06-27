"""
前端增强相关模型
- CampMap（营地地图表）
- CampMapZone（地图区域表）
- MiniGame（H5小游戏配置表）
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---- 枚举类型 ----

class MapType(str, enum.Enum):
    SVG = "svg"
    IMAGE = "image"


class MapStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class GameStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


# ---- 模型 ----

class CampMap(Base):
    """营地地图表"""

    __tablename__ = "camp_map"
    __table_args__ = (
        Index("idx_cm_site_status", "site_id", "status"),
        {"comment": "营地地图表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="地图名称",
    )
    map_image: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="底图URL",
    )
    map_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=MapType.IMAGE.value,
        server_default=MapType.IMAGE.value,
        comment="地图类型: svg/image",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=MapStatus.ACTIVE.value,
        server_default=MapStatus.ACTIVE.value,
        comment="状态: active/inactive",
    )

    # 关系
    zones: Mapped[list["CampMapZone"]] = relationship(
        back_populates="camp_map", lazy="selectin",
        cascade="all, delete-orphan",
    )


class CampMapZone(Base):
    """地图区域表"""

    __tablename__ = "camp_map_zone"
    __table_args__ = (
        Index("idx_cmz_map", "camp_map_id"),
        Index("idx_cmz_product_ids", "product_ids", postgresql_using="gin"),
        {"comment": "地图区域表"},
    )

    camp_map_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("camp_map.id"), nullable=False,
        comment="营地地图ID",
    )
    zone_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="区域名称",
    )
    zone_code: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="区域编码",
    )
    coordinates: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]",
        comment="多边形坐标点 [{x, y}]",
    )
    product_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]",
        comment="关联商品ID列表 [product_id, ...]",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="区域描述",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序",
    )
    link_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="热区链接类型: product/cms/h5/none"
    )
    link_target: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="热区链接目标"
    )
    link_label: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="热区链接按钮文案"
    )
    click_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="点击次数"
    )

    # 关系
    camp_map: Mapped["CampMap"] = relationship(
        back_populates="zones",
    )


class MiniGame(Base):
    """H5小游戏配置表"""

    __tablename__ = "mini_game"
    __table_args__ = (
        Index("idx_mg_site_status", "site_id", "status"),
        {"comment": "H5小游戏配置表"},
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="游戏名称",
    )
    cover_image: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="封面图URL",
    )
    game_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="H5游戏URL",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="游戏描述",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=GameStatus.ACTIVE.value,
        server_default=GameStatus.ACTIVE.value,
        comment="状态: active/inactive",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )
    points_reward: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="积分奖励(预留)",
    )


class PageViewStat(Base):
    """页面浏览统计聚合表"""

    __tablename__ = "page_view_stat"
    __table_args__ = (
        Index("idx_pvs_site_page_date", "site_id", "page_key", "stat_date", unique=True),
        Index("idx_pvs_site_date", "site_id", "stat_date"),
        {"comment": "页面浏览统计聚合表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    page_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="页面标识"
    )
    page_title: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="页面标题"
    )
    stat_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="统计日期"
    )
    view_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="浏览次数"
    )
    user_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="登录用户访问次数"
    )
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近访问时间"
    )
