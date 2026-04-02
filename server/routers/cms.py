"""
CMS 可视化装修系统路由

C端接口（公开）:
- GET /cms/pages/{page_code}        — 获取已发布的页面配置
- GET /cms/pages/{page_code}/check  — 检查页面版本更新
- GET /cms/landing                  — 获取企业宣传页配置

B端接口（需认证）:
- GET    /admin/cms/pages           — 页面列表
- POST   /admin/cms/pages           — 创建页面
- GET    /admin/cms/pages/{id}      — 页面详情
- PUT    /admin/cms/pages/{id}      — 更新页面信息
- DELETE /admin/cms/pages/{id}      — 删除页面（软删除）
- PUT    /admin/cms/pages/{id}/draft    — 保存草稿
- POST   /admin/cms/pages/{id}/publish  — 发布
- GET    /admin/cms/pages/{id}/versions — 版本列表
- POST   /admin/cms/pages/{id}/rollback — 回滚
- POST   /admin/cms/pages/{id}/preview  — 生成预览token
- POST   /admin/cms/pages/{id}/lock     — 获取/续期编辑锁
- DELETE /admin/cms/pages/{id}/lock     — 释放编辑锁
- GET    /admin/cms/components      — 组件列表
- POST   /admin/cms/components      — 注册组件
- GET    /admin/cms/assets          — 素材列表
- POST   /admin/cms/assets/upload   — 上传素材
- DELETE /admin/cms/assets/{id}     — 删除素材
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from schemas.cms import (
    CmsAssetListItem,
    CmsComponentCreate,
    CmsComponentListItem,
    CmsDraftSave,
    CmsPageConfigResponse,
    CmsPageCreate,
    CmsPageDetail,
    CmsPageListItem,
    CmsPageUpdate,
    CmsPreviewResponse,
    CmsPublishRequest,
    CmsRollbackRequest,
    CmsVersionCheckResponse,
    CmsVersionListItem,
)
from schemas.common import PaginatedResponse, ResponseModel
import services.cms_service as cms_service

router = APIRouter(prefix="/api/v1", tags=["CMS"])

# 独立 Limiter 实例，避免循环导入
limiter = Limiter(key_func=get_remote_address)


# ==================== C端接口（公开） ====================

@router.get("/cms/pages/{page_code}", summary="获取已发布的页面配置")
@limiter.limit("100/minute")
async def get_published_page(
    page_code: str,
    request: Request,
    preview_token: Optional[str] = Query(None, description="预览token"),
    db: AsyncSession = Depends(get_db),
):
    """
    C端渲染用。Redis 缓存 5 分钟，发布时清除。
    支持 preview_token 查看草稿预览。
    仅返回 status=active 且有已发布版本的页面。
    """
    site_id = get_site_id(request)

    if preview_token:
        # 预览模式：校验 token → 返回草稿
        data = await cms_service.get_preview_page(
            db, site_id=site_id, page_code=page_code, token=preview_token,
        )
    else:
        # 正式模式：Redis 缓存 → DB 查询
        data = await cms_service.get_published_page(
            db, site_id=site_id, page_code=page_code,
        )

    if not data:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在或未发布"},
        )

    return ResponseModel.success(data=data)


@router.get("/cms/pages/{page_code}/check", summary="检查页面版本更新")
@limiter.limit("100/minute")
async def check_page_version(
    page_code: str,
    request: Request,
    version: int = Query(..., description="当前客户端版本号"),
    db: AsyncSession = Depends(get_db),
):
    """检查页面是否有新版本"""
    site_id = get_site_id(request)
    result = await cms_service.check_version(
        db, site_id=site_id, page_code=page_code, client_version=version,
    )
    return ResponseModel.success(data=result)


@router.get("/cms/landing", summary="获取企业宣传页配置")
@limiter.limit("30/minute")
async def get_landing_page(
    request: Request,
    site_id: int = Query(1, description="营地ID", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """
    公开接口，无需登录。通过 query 参数传递 site_id（非 X-Site-Id header）。
    Redis 缓存 5 分钟，key: cms:landing:{site_id}。
    """
    # 校验 site_id 合法范围
    allowed_sites = {1, 2}  # 西郊林场=1, 大聋谷=2
    if site_id not in allowed_sites:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_SITE_ID", "message": f"site_id 必须为 {allowed_sites} 之一"},
        )

    data = await cms_service.get_published_page(
        db, site_id=site_id, page_code="admin_landing",
    )

    if not data:
        # 宣传页未配置时返回空，前端展示默认内容
        return ResponseModel.success(data=None, message="宣传页未配置")

    return ResponseModel.success(data=data)


# ==================== B端接口（需认证） ====================

@router.get("/admin/cms/pages", summary="页面列表")
async def list_pages(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    page_type: Optional[str] = Query(None, description="筛选页面类型"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取页面列表（分页、按类型筛选）"""
    site_id = get_site_id(request)
    items, total = await cms_service.list_pages(
        db, site_id=site_id, page=page, page_size=page_size, page_type=page_type,
    )
    data = [CmsPageListItem.model_validate(item) for item in items]
    return PaginatedResponse.create(
        items=[item.model_dump() for item in data],
        total=total, page=page, page_size=page_size,
    )


@router.post("/admin/cms/pages", summary="创建页面")
async def create_page(
    body: CmsPageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建 CMS 页面"""
    site_id = get_site_id(request)
    page_obj = await cms_service.create_page(db, site_id=site_id, data=body)
    return ResponseModel.success(
        data=CmsPageDetail.model_validate(page_obj).model_dump(),
    )


@router.get("/admin/cms/pages/{page_id}", summary="页面详情")
async def get_page_detail(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取页面详情（含草稿配置）"""
    site_id = get_site_id(request)
    page_obj = await cms_service.get_page(db, site_id=site_id, page_id=page_id)
    if not page_obj:
        raise HTTPException(
            status_code=404,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )
    return ResponseModel.success(
        data=CmsPageDetail.model_validate(page_obj).model_dump(),
    )


@router.put("/admin/cms/pages/{page_id}", summary="更新页面信息")
async def update_page(
    page_id: int,
    body: CmsPageUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """更新页面基本信息（标题、状态等）"""
    site_id = get_site_id(request)
    page_obj = await cms_service.update_page(
        db, site_id=site_id, page_id=page_id, data=body,
    )
    return ResponseModel.success(
        data=CmsPageDetail.model_validate(page_obj).model_dump(),
    )


@router.delete("/admin/cms/pages/{page_id}", summary="删除页面")
async def delete_page(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """软删除页面（仅 custom 类型可删）"""
    site_id = get_site_id(request)
    await cms_service.delete_page(db, site_id=site_id, page_id=page_id)
    return ResponseModel.success(message="删除成功")


@router.put("/admin/cms/pages/{page_id}/draft", summary="保存草稿")
async def save_draft(
    page_id: int,
    body: CmsDraftSave,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    保存页面草稿配置JSON。
    使用 draft_updated_at 乐观锁防止并发覆盖。
    """
    site_id = get_site_id(request)
    page_obj = await cms_service.save_draft(
        db, site_id=site_id, page_id=page_id, data=body,
    )
    return ResponseModel.success(
        data=CmsPageDetail.model_validate(page_obj).model_dump(),
    )


@router.post("/admin/cms/pages/{page_id}/reset", summary="重置页面为默认")
async def reset_page(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    重置页面：清空草稿 + 取消发布版本。
    小程序端将自动降级到默认硬编码首页。
    仅 super_admin 可执行。
    """
    if not admin.role or admin.role.role_code != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "CMS_PUBLISH_PERMISSION_DENIED", "message": "仅超级管理员可重置页面"},
        )

    site_id = get_site_id(request)
    page_obj = await cms_service.reset_page(
        db, site_id=site_id, page_id=page_id,
    )
    return ResponseModel.success(
        data=CmsPageDetail.model_validate(page_obj).model_dump(),
        message="页面已重置为默认",
    )


@router.post("/admin/cms/pages/{page_id}/publish", summary="发布页面")
async def publish_page(
    page_id: int,
    body: CmsPublishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    发布当前草稿为线上版本。仅 super_admin 可执行。
    发布后清除该页面的 C端 Redis 缓存。
    """
    # 权限校验
    if not admin.role or admin.role.role_code != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "CMS_PUBLISH_PERMISSION_DENIED", "message": "仅超级管理员可发布页面"},
        )

    site_id = get_site_id(request)
    version = await cms_service.publish_page(
        db, site_id=site_id, page_id=page_id,
        admin_id=admin.id, remark=body.remark,
    )
    return ResponseModel.success(data={
        "version_id": version.id,
        "version_number": version.version_number,
        "published_at": version.published_at.isoformat(),
    })


@router.get("/admin/cms/pages/{page_id}/versions", summary="版本列表")
async def list_versions(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取页面版本历史列表"""
    site_id = get_site_id(request)
    versions = await cms_service.list_versions(db, site_id=site_id, page_id=page_id)
    return ResponseModel.success(data=versions)


@router.post("/admin/cms/pages/{page_id}/rollback", summary="版本回滚")
async def rollback_page(
    page_id: int,
    body: CmsRollbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """回滚到指定版本。仅 super_admin 可执行。"""
    if not admin.role or admin.role.role_code != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "CMS_PUBLISH_PERMISSION_DENIED", "message": "仅超级管理员可回滚"},
        )

    site_id = get_site_id(request)
    await cms_service.rollback_page(
        db, site_id=site_id, page_id=page_id,
        version_id=body.version_id, admin_id=admin.id,
    )
    return ResponseModel.success(message="回滚成功")


@router.post("/admin/cms/pages/{page_id}/preview", summary="生成预览token")
async def create_preview(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """生成草稿预览 token（UUID → Redis，TTL=30min）"""
    site_id = get_site_id(request)
    result = await cms_service.create_preview_token(db, site_id=site_id, page_id=page_id)
    return ResponseModel.success(data=result)


@router.post("/admin/cms/pages/{page_id}/lock", summary="获取/续期编辑锁")
async def acquire_lock(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取或续期编辑锁（Redis 分布式锁，TTL=5min）"""
    success = await cms_service.acquire_edit_lock(
        page_id=page_id, admin_id=admin.id, admin_name=admin.username,
    )
    if not success:
        lock_info = await cms_service.get_lock_info(page_id=page_id)
        raise HTTPException(
            status_code=423,
            detail={
                "code": "CMS_EDIT_LOCKED",
                "message": f"该页面正在被 {lock_info.get('admin_name', '未知')} 编辑中",
                "data": lock_info,
            },
        )
    return ResponseModel.success(message="获取编辑锁成功")


@router.delete("/admin/cms/pages/{page_id}/lock", summary="释放编辑锁")
async def release_lock(
    page_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """释放编辑锁"""
    await cms_service.release_edit_lock(page_id=page_id, admin_id=admin.id)
    return ResponseModel.success(message="释放编辑锁成功")


@router.get("/admin/cms/components", summary="组件列表")
async def list_components(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取可用组件列表"""
    site_id = get_site_id(request)
    components = await cms_service.list_components(db, site_id=site_id)
    data = [CmsComponentListItem.model_validate(c).model_dump() for c in components]
    return ResponseModel.success(data=data)


@router.post("/admin/cms/components", summary="注册组件")
async def create_component(
    body: CmsComponentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """注册新组件类型（仅 super_admin）"""
    if not admin.role or admin.role.role_code != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "CMS_PUBLISH_PERMISSION_DENIED", "message": "仅超级管理员可注册组件"},
        )
    site_id = get_site_id(request)
    comp = await cms_service.create_component(db, site_id=site_id, data=body)
    return ResponseModel.success(
        data=CmsComponentListItem.model_validate(comp).model_dump(),
    )


@router.get("/admin/cms/assets", summary="素材列表")
async def list_assets(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    file_type: Optional[str] = Query(None, description="筛选: image/video"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """素材库列表（分页、按类型筛选）"""
    site_id = get_site_id(request)
    items, total = await cms_service.list_assets(
        db, site_id=site_id, page=page, page_size=page_size, file_type=file_type,
    )
    data = [CmsAssetListItem.model_validate(a).model_dump() for a in items]
    return PaginatedResponse.create(items=data, total=total, page=page, page_size=page_size)


@router.post("/admin/cms/assets/upload", summary="上传素材")
@limiter.limit("60/minute")
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    上传素材（图片/视频）。
    校验：MIME + magic bytes + 大小限制 + UUID 重命名。
    频率限制：60次/分钟/用户。
    """
    site_id = get_site_id(request)
    asset = await cms_service.upload_asset(
        db, site_id=site_id, file=file, admin_id=admin.id,
    )
    return ResponseModel.success(
        data=CmsAssetListItem.model_validate(asset).model_dump(),
    )


@router.delete("/admin/cms/assets/{asset_id}", summary="删除素材")
async def delete_asset(
    asset_id: int,
    request: Request,
    force: bool = Query(False, description="强制删除（忽略引用检测）"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    删除素材。删除前扫描所有页面配置中的 URL 引用。
    有引用时拒绝删除（除非 force=true 且为 super_admin）。
    """
    site_id = get_site_id(request)

    if force and admin.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "CMS_PUBLISH_PERMISSION_DENIED", "message": "仅超级管理员可强制删除"},
        )

    await cms_service.delete_asset(
        db, site_id=site_id, asset_id=asset_id, force=force,
    )
    return ResponseModel.success(message="删除成功")
