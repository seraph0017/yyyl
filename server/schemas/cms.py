"""
CMS 可视化装修系统 Schema
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 页面 Schema ----

class CmsPageCreate(BaseModel):
    """创建页面请求"""
    model_config = ConfigDict(populate_by_name=True)

    page_code: str = Field(
        ..., min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]{1,63}$",
        description="页面标识",
    )
    page_type: str = Field(
        ..., description="页面类型: home/activity/promotion/custom/landing",
    )
    title: str = Field(..., min_length=1, max_length=128, description="页面标题")
    description: Optional[str] = Field(None, max_length=500, description="页面描述")
    status: str = Field("active", description="页面状态: active/inactive")

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: str) -> str:
        allowed = {"home", "activity", "promotion", "custom", "landing"}
        if v not in allowed:
            raise ValueError(f"page_type 必须为 {allowed} 之一")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in {"active", "inactive"}:
            raise ValueError("status 必须为 active 或 inactive")
        return v


class CmsPageUpdate(BaseModel):
    """更新页面基本信息"""
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(None, min_length=1, max_length=128, description="页面标题")
    description: Optional[str] = Field(None, max_length=500, description="页面描述")
    status: Optional[str] = Field(None, description="页面状态")
    sort_order: Optional[int] = Field(None, ge=0, description="排序")


class CmsPageListItem(BaseModel):
    """页面列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    page_code: str
    page_type: str
    title: str
    status: str
    current_version_id: Optional[int] = None
    draft_updated_at: Optional[datetime] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CmsPageDetail(BaseModel):
    """页面详情（含草稿配置）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    page_code: str
    page_type: str
    title: str
    description: Optional[str] = None
    status: str
    current_version_id: Optional[int] = None
    draft_config: Optional[Dict[str, Any]] = None
    draft_updated_at: Optional[datetime] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ---- 草稿 Schema ----

class CmsDraftSave(BaseModel):
    """保存草稿请求"""
    model_config = ConfigDict(populate_by_name=True)

    config: Dict[str, Any] = Field(..., description="页面配置JSON")
    draft_updated_at: Optional[datetime] = Field(
        None, description="上次获取的草稿时间戳（乐观锁）",
    )

    @field_validator("config")
    @classmethod
    def validate_config_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """校验配置JSON大小不超过500KB"""
        import json
        size = len(json.dumps(v, ensure_ascii=False).encode("utf-8"))
        if size > 500 * 1024:
            raise ValueError("配置JSON大小超过500KB限制")
        return v


# ---- 发布/回滚 Schema ----

class CmsPublishRequest(BaseModel):
    """发布请求"""
    remark: Optional[str] = Field(None, max_length=256, description="发布备注")


class CmsRollbackRequest(BaseModel):
    """回滚请求"""
    version_id: int = Field(..., description="目标版本ID")


# ---- 版本 Schema ----

class CmsVersionListItem(BaseModel):
    """版本列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_number: int
    published_by: int
    published_at: datetime
    remark: Optional[str] = None
    is_current: bool = Field(False, description="是否为当前发布版本")


# ---- 预览 Schema ----

class CmsPreviewResponse(BaseModel):
    """预览响应"""
    preview_token: str
    preview_url: str
    expires_at: datetime


# ---- 编辑锁 Schema ----

class CmsLockInfo(BaseModel):
    """编辑锁信息"""
    admin_id: int
    admin_name: str
    locked_at: str


# ---- 组件 Schema ----

class CmsComponentListItem(BaseModel):
    """组件列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    component_type: str
    name: str
    icon: Optional[str] = None
    default_config: Optional[Dict[str, Any]] = None
    status: str
    sort_order: int


class CmsComponentCreate(BaseModel):
    """注册组件"""
    component_type: str = Field(..., max_length=32, description="组件类型标识")
    name: str = Field(..., max_length=64, description="组件显示名称")
    icon: Optional[str] = Field(None, max_length=128, description="图标URL")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置模板")


# ---- 素材 Schema ----

class CmsAssetListItem(BaseModel):
    """素材列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    uploaded_by: int
    created_at: datetime


# ---- C端响应 Schema ----

class CmsPageConfigResponse(BaseModel):
    """C端页面配置响应"""
    page_code: str
    title: str
    version: int
    config: Dict[str, Any]
    updated_at: datetime


class CmsVersionCheckResponse(BaseModel):
    """版本检查响应"""
    has_update: bool
    latest_version: Optional[int] = None
