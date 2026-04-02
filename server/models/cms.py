"""
CMS 可视化装修系统数据模型
- CmsPage（CMS 页面主表）
- CmsPageVersion（页面版本历史）
- CmsComponent（可用组件注册表）
- CmsAsset（CMS 素材库）
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class CmsPage(Base):
    """CMS 页面主表"""

    __tablename__ = "cms_page"
    __table_args__ = (
        # 条件唯一索引：仅对未删除记录约束唯一（支持软删除后重建同 page_code）
        Index(
            "uq_cms_page_site_code", "site_id", "page_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_cms_page_site_type", "site_id", "page_type", "status"),
        {"comment": "CMS 页面主表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )
    page_code: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="页面标识，同一营地下唯一",
    )
    page_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="页面类型: home/activity/promotion/custom/landing",
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False,
        comment="页面标题",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="页面描述",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active",
        comment="页面状态: active/inactive",
    )
    current_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True,
        comment="当前发布版本ID（逻辑引用，非FK，避免循环依赖）",
    )
    draft_config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="草稿配置JSON",
    )
    draft_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="草稿最后更新时间（乐观锁）",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序权重",
    )

    # 关系
    versions: Mapped[List["CmsPageVersion"]] = relationship(
        back_populates="page", lazy="noload",
    )


class CmsPageVersion(Base):
    """页面版本历史"""

    __tablename__ = "cms_page_version"
    __table_args__ = (
        # DESC 索引：最新版本优先查询
        Index("idx_cms_pv_page", "page_id", "version_number", postgresql_ops={"version_number": "DESC"}),
        Index("idx_cms_pv_published_at", "published_at", postgresql_ops={"published_at": "DESC"}),
        {"comment": "CMS 页面版本历史"},
    )

    page_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cms_page.id"), nullable=False,
        comment="所属页面ID",
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="版本序号",
    )
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="页面配置JSON快照",
    )
    published_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=False,
        comment="发布人ID",
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="发布时间",
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True,
        comment="发布备注",
    )

    # 关系
    page: Mapped["CmsPage"] = relationship(back_populates="versions")


class CmsComponent(Base):
    """可用组件注册表"""

    __tablename__ = "cms_component"
    __table_args__ = (
        Index("idx_cms_comp_site_status", "site_id", "status", "sort_order"),
        {"comment": "CMS 可用组件注册表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )
    component_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="组件类型标识: banner/image/image_text/notice/nav/product_list/coupon/rich_text/spacer/divider/video",
    )
    name: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="组件显示名称",
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
        comment="组件图标URL",
    )
    default_config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="默认配置模板",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active",
        comment="状态: active/inactive",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="排序",
    )


class CmsAsset(Base):
    """CMS 素材库"""

    __tablename__ = "cms_asset"
    __table_args__ = (
        Index("idx_cms_asset_site", "site_id", "file_type"),
        Index("idx_cms_asset_uploaded_by", "uploaded_by"),
        {"comment": "CMS 素材库"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1",
        comment="营地ID",
    )
    file_name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="文件名（UUID重命名后）",
    )
    file_url: Mapped[str] = mapped_column(
        String(512), nullable=False,
        comment="文件访问URL",
    )
    file_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="文件类型: image/video",
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="文件大小（字节）",
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="图片宽度（px）",
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="图片高度（px）",
    )
    uploaded_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_user.id"), nullable=False,
        comment="上传人ID",
    )
