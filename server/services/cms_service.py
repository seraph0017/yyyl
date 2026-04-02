"""
CMS 业务逻辑服务
模块级函数模式，与 product_service.py 等保持一致。
db 作为第一个参数传入。
"""

import json
import mimetypes
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.admin import OperationLog
from models.cms import CmsAsset, CmsComponent, CmsPage, CmsPageVersion
from redis_client import get_redis
from schemas.cms import (
    CmsComponentCreate,
    CmsDraftSave,
    CmsPageCreate,
    CmsPageUpdate,
)
from utils.sanitize import sanitize_cms_config

# ---- 组件类型白名单（JSON Schema 基础校验） ----

ALLOWED_COMPONENT_TYPES = {
    "banner", "image", "image_text", "notice", "nav",
    "product_list", "coupon", "rich_text", "spacer", "divider", "video",
}

# ---- 素材上传常量 ----

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm"}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXTS = {".mp4", ".webm"}

MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB


def _validate_config_schema(config: dict) -> None:
    """基本 JSON Schema 校验：检查组件 type 白名单"""
    components = config.get("components", [])
    for idx, comp in enumerate(components):
        comp_type = comp.get("type")
        if not comp_type:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "CMS_CONFIG_INVALID",
                    "message": f"第 {idx + 1} 个组件缺少 type 字段",
                },
            )
        if comp_type not in ALLOWED_COMPONENT_TYPES:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "CMS_CONFIG_INVALID",
                    "message": f"第 {idx + 1} 个组件类型 '{comp_type}' 不在允许列表中",
                },
            )


# ---- Redis 缓存操作（使用全局单例） ----

async def _get_cached_page(site_id: int, page_code: str) -> Optional[dict]:
    """从 Redis 获取缓存的页面配置"""
    redis = get_redis()
    key = f"cms:page:{site_id}:{page_code}"
    data = await redis.get(key)
    if data:
        return json.loads(data)
    return None


async def _set_cached_page(site_id: int, page_code: str, data: dict) -> None:
    """设置页面配置缓存（5分钟）"""
    redis = get_redis()
    key = f"cms:page:{site_id}:{page_code}"
    await redis.setex(key, 300, json.dumps(data, ensure_ascii=False, default=str))


async def _clear_page_cache(site_id: int, page_code: str) -> None:
    """清除页面配置缓存"""
    redis = get_redis()
    await redis.delete(f"cms:page:{site_id}:{page_code}")
    # 如果是 landing 类型，同时清除宣传页缓存
    await redis.delete(f"cms:landing:{site_id}")


# ---- C端：获取已发布页面 ----

async def get_published_page(
    db: AsyncSession, *, site_id: int, page_code: str,
) -> Optional[dict]:
    """获取已发布的页面配置（带缓存）"""
    # 1. 查缓存
    cached = await _get_cached_page(site_id, page_code)
    if cached:
        return cached

    # 2. 查数据库
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.site_id == site_id,
            CmsPage.page_code == page_code,
            CmsPage.status == "active",
            CmsPage.is_deleted.is_(False),
            CmsPage.current_version_id.isnot(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        return None

    # 3. 获取当前发布版本
    ver_result = await db.execute(
        select(CmsPageVersion).where(
            CmsPageVersion.id == page.current_version_id,
        )
    )
    version = ver_result.scalar_one_or_none()
    if not version:
        return None

    data = {
        "page_code": page.page_code,
        "title": page.title,
        "version": version.version_number,
        "config": version.config,
        "updated_at": version.published_at.isoformat(),
    }

    # 4. 写缓存
    await _set_cached_page(site_id, page_code, data)
    return data


# ---- C端：通过预览 token 获取草稿 ----

async def get_preview_page(
    db: AsyncSession, *, site_id: int, page_code: str, token: str,
) -> Optional[dict]:
    """通过预览 token 获取草稿配置"""
    redis = get_redis()
    token_data = await redis.get(f"cms:preview:{token}")
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail={"code": "CMS_PREVIEW_TOKEN_INVALID", "message": "预览token无效或已过期"},
        )

    payload = json.loads(token_data)
    # 校验 token 对应的 site_id 一致
    if payload.get("site_id") != site_id:
        raise HTTPException(
            status_code=401,
            detail={"code": "CMS_PREVIEW_TOKEN_INVALID", "message": "预览token与当前营地不匹配"},
        )

    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == payload["page_id"],
            CmsPage.page_code == page_code,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page or not page.draft_config:
        return None

    return {
        "page_code": page.page_code,
        "title": page.title,
        "version": 0,  # 草稿标识
        "config": page.draft_config,
        "updated_at": (page.draft_updated_at or page.updated_at).isoformat(),
    }


# ---- C端：版本检查 ----

async def check_version(
    db: AsyncSession, *, site_id: int, page_code: str, client_version: int,
) -> dict:
    """检查页面是否有新版本"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.site_id == site_id,
            CmsPage.page_code == page_code,
            CmsPage.status == "active",
            CmsPage.is_deleted.is_(False),
            CmsPage.current_version_id.isnot(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        return {"has_update": False, "latest_version": None}

    # 获取当前发布版本号
    ver_result = await db.execute(
        select(CmsPageVersion.version_number).where(
            CmsPageVersion.id == page.current_version_id,
        )
    )
    latest_version = ver_result.scalar_one_or_none()
    if latest_version is None:
        return {"has_update": False, "latest_version": None}

    return {
        "has_update": latest_version > client_version,
        "latest_version": latest_version,
    }


# ---- B端：页面列表 ----

async def list_pages(
    db: AsyncSession, *, site_id: int, page: int, page_size: int,
    page_type: Optional[str] = None,
) -> Tuple[List[CmsPage], int]:
    """页面列表（分页、按类型筛选）"""
    conditions = [
        CmsPage.site_id == site_id,
        CmsPage.is_deleted.is_(False),
    ]
    if page_type:
        conditions.append(CmsPage.page_type == page_type)

    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(CmsPage).where(*conditions)
    )
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(
        select(CmsPage)
        .where(*conditions)
        .order_by(CmsPage.sort_order.asc(), CmsPage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return items, total


# ---- B端：创建页面 ----

async def create_page(
    db: AsyncSession, *, site_id: int, data: CmsPageCreate,
) -> CmsPage:
    """创建 CMS 页面"""
    # 检查 page_code 唯一性
    existing = await db.execute(
        select(CmsPage).where(
            CmsPage.site_id == site_id,
            CmsPage.page_code == data.page_code,
            CmsPage.is_deleted.is_(False),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"code": "CMS_PAGE_CODE_DUPLICATE", "message": f"页面标识 '{data.page_code}' 已存在"},
        )

    page = CmsPage(
        site_id=site_id,
        page_code=data.page_code,
        page_type=data.page_type,
        title=data.title,
        description=data.description,
        status=data.status,
    )
    db.add(page)
    await db.flush()
    await db.refresh(page)
    return page


# ---- B端：获取页面详情 ----

async def get_page(
    db: AsyncSession, *, site_id: int, page_id: int,
) -> Optional[CmsPage]:
    """获取页面详情"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


# ---- B端：更新页面基本信息 ----

async def update_page(
    db: AsyncSession, *, site_id: int, page_id: int, data: CmsPageUpdate,
) -> CmsPage:
    """更新页面基本信息（标题、状态等）"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)

    await db.flush()
    await db.refresh(page)
    return page


# ---- B端：软删除页面 ----

async def delete_page(
    db: AsyncSession, *, site_id: int, page_id: int,
) -> None:
    """软删除页面，仅 custom 类型可删"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    if page.page_type != "custom":
        raise HTTPException(
            status_code=400,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "仅 custom 类型页面可删除"},
        )

    page.is_deleted = True
    await db.flush()

    # 清除 C端缓存
    await _clear_page_cache(site_id, page.page_code)


# ---- B端：保存草稿（乐观锁 + JSON Schema 校验） ----

async def save_draft(
    db: AsyncSession, *, site_id: int, page_id: int, data: CmsDraftSave,
) -> CmsPage:
    """保存草稿，使用 draft_updated_at 乐观锁"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    # 乐观锁检测
    if data.draft_updated_at and page.draft_updated_at:
        if page.draft_updated_at > data.draft_updated_at:
            raise HTTPException(
                status_code=409,
                detail={"code": "CMS_DRAFT_CONFLICT", "message": "草稿已被其他管理员修改，请刷新后重试"},
            )

    # 校验组件数量
    components = data.config.get("components", [])
    if len(components) > 30:
        raise HTTPException(
            status_code=400,
            detail={"code": "CMS_COMPONENT_LIMIT_EXCEEDED", "message": "组件数量超过30个上限"},
        )

    # JSON Schema 基础校验：组件 type 白名单
    _validate_config_schema(data.config)

    # 富文本 XSS 过滤
    sanitized_config = sanitize_cms_config(data.config)

    page.draft_config = sanitized_config
    page.draft_updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(page)
    return page


# ---- B端：重置页面（清空草稿 + 取消发布版本） ----

async def reset_page(
    db: AsyncSession, *, site_id: int, page_id: int,
) -> CmsPage:
    """重置页面：清空草稿配置并取消当前发布版本，使小程序回退到默认首页"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    page.draft_config = None
    page.draft_updated_at = None
    page.current_version_id = None
    await db.flush()
    await db.refresh(page)

    # 清除 C端缓存
    redis = get_redis()
    await redis.delete(f"cms:page:{site_id}:{page.page_code}")

    return page


# ---- B端：发布（含操作日志） ----

async def publish_page(
    db: AsyncSession, *, site_id: int, page_id: int, admin_id: int, remark: Optional[str],
) -> CmsPageVersion:
    """发布当前草稿为线上版本"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )
    if not page.draft_config:
        raise HTTPException(
            status_code=400,
            detail={"code": "CMS_DRAFT_EMPTY", "message": "草稿为空，无法发布"},
        )

    # 计算版本号
    count_result = await db.execute(
        select(func.count()).where(CmsPageVersion.page_id == page_id)
    )
    version_number = count_result.scalar() + 1

    # 创建版本快照
    version = CmsPageVersion(
        page_id=page_id,
        version_number=version_number,
        config=page.draft_config,
        published_by=admin_id,
        published_at=datetime.now(timezone.utc),
        remark=remark,
    )
    db.add(version)
    await db.flush()

    # 更新当前发布版本
    page.current_version_id = version.id
    await db.flush()

    # 清除 C端缓存
    await _clear_page_cache(site_id, page.page_code)

    # 写入操作日志
    db.add(OperationLog(
        operator_id=admin_id,
        operator_name="system",
        action="cms_publish",
        target_type="cms_page",
        target_id=page_id,
        detail={"message": f"发布页面「{page.title}」v{version_number}，备注：{remark or '无'}"},
        site_id=site_id,
    ))
    await db.flush()

    return version


# ---- B端：版本列表 ----

async def list_versions(
    db: AsyncSession, *, site_id: int, page_id: int,
) -> List[dict]:
    """获取页面版本历史列表"""
    # 先确认页面存在
    page_result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    result = await db.execute(
        select(CmsPageVersion)
        .where(
            CmsPageVersion.page_id == page_id,
            CmsPageVersion.is_deleted.is_(False),
        )
        .order_by(CmsPageVersion.version_number.desc())
    )
    versions = result.scalars().all()

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "published_by": v.published_by,
            "published_at": v.published_at.isoformat(),
            "remark": v.remark,
            "is_current": v.id == page.current_version_id,
        }
        for v in versions
    ]


# ---- B端：回滚（含操作日志） ----

async def rollback_page(
    db: AsyncSession, *, site_id: int, page_id: int, version_id: int, admin_id: int,
) -> None:
    """回滚到指定版本"""
    # 查询页面
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    # 目标版本已是当前版本
    if page.current_version_id == version_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "CMS_VERSION_IS_CURRENT", "message": "目标版本已是当前发布版本"},
        )

    # 查询目标版本
    ver_result = await db.execute(
        select(CmsPageVersion).where(
            CmsPageVersion.id == version_id,
            CmsPageVersion.page_id == page_id,
            CmsPageVersion.is_deleted.is_(False),
        )
    )
    target_version = ver_result.scalar_one_or_none()
    if not target_version:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_VERSION_NOT_FOUND", "message": "版本不存在或已被清理"},
        )

    # 更新当前发布版本
    page.current_version_id = version_id
    # 同步草稿为目标版本配置
    page.draft_config = target_version.config
    page.draft_updated_at = datetime.now(timezone.utc)
    await db.flush()

    # 清除 C端缓存
    await _clear_page_cache(site_id, page.page_code)

    # 写入操作日志
    db.add(OperationLog(
        operator_id=admin_id,
        operator_name="system",
        action="cms_rollback",
        target_type="cms_page",
        target_id=page_id,
        detail={"message": f"回滚页面「{page.title}」到 v{target_version.version_number}"},
        site_id=site_id,
    ))
    await db.flush()


# ---- B端：预览 ----

async def create_preview_token(
    db: AsyncSession, *, site_id: int, page_id: int,
) -> dict:
    """生成预览 token"""
    result = await db.execute(
        select(CmsPage).where(
            CmsPage.id == page_id,
            CmsPage.site_id == site_id,
            CmsPage.is_deleted.is_(False),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )

    token = str(uuid.uuid4())
    redis = get_redis()
    await redis.setex(
        f"cms:preview:{token}", 1800,  # TTL=30分钟
        json.dumps({"page_id": page_id, "site_id": site_id}),
    )

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    return {
        "preview_token": token,
        "preview_url": f"/api/v1/cms/pages/{page.page_code}?preview_token={token}",
        "expires_at": expires_at.isoformat(),
    }


# ---- B端：编辑锁（纯 Redis 操作，无需 db） ----

async def acquire_edit_lock(
    *, page_id: int, admin_id: int, admin_name: str,
) -> bool:
    """获取或续期编辑锁"""
    redis = get_redis()
    key = f"cms:edit_lock:{page_id}"

    # 检查是否已被锁定
    existing = await redis.get(key)
    if existing:
        lock_data = json.loads(existing)
        if lock_data["admin_id"] != admin_id:
            return False  # 被其他人锁定
        # 同一人续期

    lock_value = json.dumps({
        "admin_id": admin_id,
        "admin_name": admin_name,
        "locked_at": datetime.now(timezone.utc).isoformat(),
    })
    await redis.setex(key, 300, lock_value)  # TTL=5分钟
    return True


async def get_lock_info(*, page_id: int) -> dict:
    """获取锁持有者信息"""
    redis = get_redis()
    key = f"cms:edit_lock:{page_id}"
    data = await redis.get(key)
    if data:
        return json.loads(data)
    return {}


async def release_edit_lock(*, page_id: int, admin_id: int) -> None:
    """释放编辑锁（仅锁持有者可释放）"""
    redis = get_redis()
    key = f"cms:edit_lock:{page_id}"
    existing = await redis.get(key)
    if existing:
        lock_data = json.loads(existing)
        if lock_data["admin_id"] == admin_id:
            await redis.delete(key)


# ---- B端：组件列表 ----

async def list_components(
    db: AsyncSession, *, site_id: int,
) -> List[CmsComponent]:
    """获取可用组件列表"""
    result = await db.execute(
        select(CmsComponent)
        .where(
            CmsComponent.site_id == site_id,
            CmsComponent.status == "active",
            CmsComponent.is_deleted.is_(False),
        )
        .order_by(CmsComponent.sort_order.asc())
    )
    return list(result.scalars().all())


# ---- B端：注册组件 ----

async def create_component(
    db: AsyncSession, *, site_id: int, data: CmsComponentCreate,
) -> CmsComponent:
    """注册新组件类型"""
    comp = CmsComponent(
        site_id=site_id,
        component_type=data.component_type,
        name=data.name,
        icon=data.icon,
        default_config=data.default_config,
    )
    db.add(comp)
    await db.flush()
    await db.refresh(comp)
    return comp


# ---- B端：素材列表 ----

async def list_assets(
    db: AsyncSession, *, site_id: int, page: int, page_size: int,
    file_type: Optional[str] = None,
) -> Tuple[List[CmsAsset], int]:
    """素材库列表（分页、按类型筛选）"""
    conditions = [
        CmsAsset.site_id == site_id,
        CmsAsset.is_deleted.is_(False),
    ]
    if file_type:
        conditions.append(CmsAsset.file_type == file_type)

    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(CmsAsset).where(*conditions)
    )
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(
        select(CmsAsset)
        .where(*conditions)
        .order_by(CmsAsset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return items, total


# ---- B端：上传素材 ----

async def upload_asset(
    db: AsyncSession, *, site_id: int, file: UploadFile, admin_id: int,
) -> CmsAsset:
    """上传素材"""
    # 1. 文件扩展名检测
    ext = Path(file.filename or "").suffix.lower()
    if ext in ALLOWED_IMAGE_EXTS:
        file_type = "image"
        max_size = MAX_IMAGE_SIZE
        allowed_mimes = ALLOWED_IMAGE_TYPES
    elif ext in ALLOWED_VIDEO_EXTS:
        file_type = "video"
        max_size = MAX_VIDEO_SIZE
        allowed_mimes = ALLOWED_VIDEO_TYPES
    else:
        raise HTTPException(status_code=400, detail={
            "code": "CMS_ASSET_TYPE_NOT_ALLOWED", "message": "不支持的文件类型",
        })

    # 2. 读取文件内容
    content = await file.read()

    # 3. 大小检测
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail={
            "code": "CMS_ASSET_TOO_LARGE",
            "message": "文件大小超过限制（图片≤10MB，视频≤100MB）",
        })

    # 4. MIME type 检测
    if file.content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail={
            "code": "CMS_ASSET_MIME_MISMATCH", "message": "文件MIME类型不匹配",
        })

    # 5. 基于扩展名的 MIME 二次校验（替代 magic bytes，避免 libmagic 系统依赖）
    guessed_mime, _ = mimetypes.guess_type(file.filename or "")
    if guessed_mime and guessed_mime not in allowed_mimes:
        raise HTTPException(status_code=400, detail={
            "code": "CMS_ASSET_MIME_MISMATCH", "message": "文件实际类型与扩展名不匹配",
        })

    # 6. UUID 重命名
    new_filename = f"{uuid.uuid4()}{ext}"
    save_dir = Path("images/cms")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / new_filename

    # 7. 写入磁盘
    with open(save_path, "wb") as f:
        f.write(content)

    # 8. 获取图片尺寸
    width, height = None, None
    if file_type == "image":
        from PIL import Image
        img = Image.open(save_path)
        width, height = img.size
        # 分辨率限制
        if width > 8000 or height > 8000:
            os.remove(save_path)
            raise HTTPException(status_code=400, detail={
                "code": "CMS_ASSET_TOO_LARGE", "message": "图片分辨率超过8000×8000限制",
            })

    # 9. 存储容量检测（查询当前营地总容量）
    total_result = await db.execute(
        select(func.sum(CmsAsset.file_size)).where(
            CmsAsset.site_id == site_id,
            CmsAsset.is_deleted.is_(False),
        )
    )
    total_size = total_result.scalar() or 0
    if total_size + len(content) > 10 * 1024 * 1024 * 1024:  # 10GB
        os.remove(save_path)
        raise HTTPException(status_code=400, detail={
            "code": "CMS_ASSET_STORAGE_EXCEEDED", "message": "营地素材存储容量已满（上限10GB）",
        })

    # 10. 创建记录
    asset = CmsAsset(
        site_id=site_id,
        file_name=new_filename,
        file_url=f"/images/cms/{new_filename}",
        file_type=file_type,
        file_size=len(content),
        width=width,
        height=height,
        uploaded_by=admin_id,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


# ---- B端：删除素材（含 JSONB 引用检测） ----

async def delete_asset(
    db: AsyncSession, *, site_id: int, asset_id: int, force: bool = False,
) -> None:
    """删除素材，删除前扫描 JSONB 字段中的 URL 引用"""
    result = await db.execute(
        select(CmsAsset).where(
            CmsAsset.id == asset_id,
            CmsAsset.site_id == site_id,
            CmsAsset.is_deleted.is_(False),
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "素材不存在"},
        )

    if not force:
        # 检查素材是否被页面引用（扫描 draft_config 和已发布版本 config）
        url_pattern = f"%{asset.file_url}%"

        # 检查草稿引用
        draft_refs = await db.execute(
            select(CmsPage.id, CmsPage.title).where(
                cast(CmsPage.draft_config, String).like(url_pattern),
                CmsPage.site_id == site_id,
                CmsPage.is_deleted.is_(False),
            )
        )
        # 检查已发布版本引用
        version_refs = await db.execute(
            select(CmsPageVersion.page_id).where(
                cast(CmsPageVersion.config, String).like(url_pattern),
                CmsPageVersion.is_deleted.is_(False),
            ).distinct()
        )

        ref_pages = draft_refs.all()
        ref_version_pages = version_refs.all()

        if ref_pages or ref_version_pages:
            page_titles = [r.title for r in ref_pages]
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CMS_ASSET_IN_USE",
                    "message": f"素材被以下页面引用，无法删除：{', '.join(page_titles) or '已发布版本'}",
                },
            )

    # 软删除
    asset.is_deleted = True
    await db.flush()
