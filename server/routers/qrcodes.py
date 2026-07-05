"""
v1.7 小程序码路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from schemas.common import PaginatedResponse, ResponseModel
from schemas.qrcode import QrcodeCreateRequest, QrcodeResponse, QrcodeStatusUpdateRequest
import services.qrcode_service as qrcode_service

router = APIRouter(prefix="/api/v1", tags=["小程序码"])


def _get_admin_role_code(admin: AdminUser) -> str:
    return getattr(getattr(admin, "role", None), "role_code", "") or ""


def _ensure_admin_site_access(admin: AdminUser, site_id: int) -> None:
    if _get_admin_role_code(admin) == "super_admin":
        return
    if getattr(admin, "site_id", None) != site_id:
        raise HTTPException(
            status_code=403,
            detail={"code": 40311, "message": "无权操作其他营地数据"},
        )


@router.post("/admin/qrcodes", summary="创建或复用小程序码")
async def create_qrcode(
    body: QrcodeCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建或复用小程序码。"""
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    qrcode = await qrcode_service.create_or_reuse_qrcode(
        db,
        site_id=site_id,
        body=body,
        generated_by=admin.id,
    )
    return ResponseModel.success(
        data=QrcodeResponse.model_validate(qrcode).model_dump(mode="json")
    )


@router.get("/admin/qrcodes", summary="小程序码列表")
async def list_qrcodes(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    target_type: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    items, total = await qrcode_service.list_qrcodes(
        db,
        site_id=site_id,
        page=page,
        page_size=page_size,
        target_type=target_type,
        channel=channel,
        status=status,
    )
    return PaginatedResponse.create(
        items=[QrcodeResponse.model_validate(item).model_dump(mode="json") for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/qrcodes/{qrcode_id}", summary="小程序码详情")
async def get_qrcode_detail(
    qrcode_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    qrcode = await qrcode_service.get_qrcode(db, site_id=site_id, qrcode_id=qrcode_id)
    if not qrcode:
        return ResponseModel.error(code=40404, message="小程序码不存在")
    return ResponseModel.success(
        data=QrcodeResponse.model_validate(qrcode).model_dump(mode="json")
    )


@router.post("/admin/qrcodes/{qrcode_id}/regenerate", summary="重新生成小程序码")
async def regenerate_qrcode(
    qrcode_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    qrcode = await qrcode_service.regenerate_qrcode(
        db,
        site_id=site_id,
        qrcode_id=qrcode_id,
        generated_by=admin.id,
    )
    return ResponseModel.success(
        data=QrcodeResponse.model_validate(qrcode).model_dump(mode="json")
    )


@router.patch("/admin/qrcodes/{qrcode_id}/status", summary="更新小程序码状态")
async def update_qrcode_status(
    qrcode_id: int,
    body: QrcodeStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    qrcode = await qrcode_service.update_qrcode_status(
        db,
        site_id=site_id,
        qrcode_id=qrcode_id,
        status_value=body.status,
    )
    return ResponseModel.success(
        data=QrcodeResponse.model_validate(qrcode).model_dump(mode="json")
    )


@router.get("/admin/qrcodes/{qrcode_id}/download", summary="下载小程序码图片")
async def download_qrcode(
    qrcode_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    image_path = await qrcode_service.get_transparent_qrcode_image_path(
        db,
        site_id=site_id,
        qrcode_id=qrcode_id,
    )
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=image_path.name,
    )


@router.get("/qrcodes/resolve", summary="解析小程序码")
async def resolve_qrcode(
    request: Request,
    scene: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    site_id = get_site_id(request)
    data = await qrcode_service.resolve_qrcode(
        db,
        site_id=site_id,
        scene=scene,
    )
    return ResponseModel.success(data=data.model_dump())
