"""
小程序码服务

负责生成微信小程序码、维护二维码记录，以及扫码解析归因。
"""

from __future__ import annotations

import json
import hashlib
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.cms import CmsPage
from models.qrcode import MiniProgramQRCode, MiniProgramQRCodeScanLog
from redis_client import get_redis
from schemas.qrcode import QrcodeCreateRequest, QrcodeResolveResponse
import services.cms_service as cms_service


WECHAT_API_BASE = "https://api.weixin.qq.com"
QRCODE_ATTRIBUTION_TTL_SECONDS = 86400
QRCODE_IMAGE_DIR = Path(__file__).resolve().parents[1] / "images" / "qrcodes"
TEMPORARY_QRCODE_IMAGE_DIR = QRCODE_IMAGE_DIR / "temporary"
TRANSPARENT_QRCODE_IMAGE_DIR = QRCODE_IMAGE_DIR / "transparent"


class QrcodeServiceError(Exception):
    """小程序码服务内部错误"""


@dataclass(frozen=True)
class WechatMiniProgramConfig:
    app_id: str
    app_secret: str


def build_target_path(target_type: str, target_key: str) -> str:
    """根据目标类型生成白名单内的小程序内部路径。"""
    if target_type in {"product", "activity_product"}:
        return f"/pages/product-detail/index?id={target_key}"
    if target_type == "category":
        return f"/pages/category/index?category={target_key}"
    if target_type in {"custom_page", "activity_page"}:
        return f"/pages/cms-page/index?page_code={target_key}"
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "QRCODE_TARGET_TYPE_INVALID", "message": "不支持的二维码目标类型"},
    )


async def create_or_reuse_qrcode(
    db: AsyncSession,
    *,
    site_id: int,
    body: QrcodeCreateRequest,
    generated_by: Optional[int] = None,
) -> MiniProgramQRCode:
    """创建或复用同营地、同目标、同渠道的小程序码。"""
    existing = await _find_existing_qrcode(
        db,
        site_id=site_id,
        target_type=body.target_type,
        target_key=body.target_key,
        channel=body.channel,
    )
    if existing:
        if generated_by and existing.image_url:
            await cms_service.register_existing_asset(
                db,
                site_id=site_id,
                file_url=existing.image_url,
                file_name=Path(existing.image_url).name,
                file_type="qrcode",
                admin_id=generated_by,
            )
        return existing

    await _validate_target_can_generate(
        db,
        site_id=site_id,
        target_type=body.target_type,
        target_key=body.target_key,
    )

    short_code = await _generate_unique_short_code(db)
    path = build_target_path(body.target_type, body.target_key)
    now = datetime.now(timezone.utc)
    qrcode = MiniProgramQRCode(
        site_id=site_id,
        target_type=body.target_type,
        target_key=body.target_key,
        title=body.title,
        path=path,
        scene=short_code,
        short_code=short_code,
        channel=body.channel,
        status="active",
        generated_by=generated_by,
        generated_at=now,
    )
    db.add(qrcode)
    await db.flush()

    qrcode.image_url = await _create_wechat_qrcode_image(
        site_id=site_id,
        scene=short_code,
        path=path,
        target_type=body.target_type,
    )
    if generated_by and qrcode.image_url:
        await cms_service.register_existing_asset(
            db,
            site_id=site_id,
            file_url=qrcode.image_url,
            file_name=Path(qrcode.image_url).name,
            file_type="qrcode",
            admin_id=generated_by,
        )
    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(qrcode)
    return qrcode


async def create_or_reuse_cms_page_qrcode(
    db: AsyncSession,
    *,
    site_id: int,
    page_id: int,
    generated_by: Optional[int] = None,
) -> MiniProgramQRCode:
    """为已发布 CMS 页面创建或复用小程序码。"""
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CMS_PAGE_NOT_FOUND", "message": "页面不存在"},
        )
    body = QrcodeCreateRequest(
        target_type="activity_page" if page.page_type == "activity" else "custom_page",
        target_key=page.page_code,
        title=page.title,
        channel="cms",
    )
    return await create_or_reuse_qrcode(
        db,
        site_id=site_id,
        body=body,
        generated_by=generated_by,
    )


async def list_qrcodes(
    db: AsyncSession,
    *,
    site_id: int,
    page: int,
    page_size: int,
    target_type: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[list[MiniProgramQRCode], int]:
    """分页查询小程序码。"""
    conditions = [
        MiniProgramQRCode.site_id == site_id,
        MiniProgramQRCode.is_deleted.is_(False),
    ]
    if target_type:
        conditions.append(MiniProgramQRCode.target_type == target_type)
    if channel:
        conditions.append(MiniProgramQRCode.channel == channel)
    if status:
        conditions.append(MiniProgramQRCode.status == status)

    count_result = await db.execute(
        select(func.count(MiniProgramQRCode.id)).where(and_(*conditions))
    )
    total = count_result.scalar_one()
    result = await db.execute(
        select(MiniProgramQRCode)
        .where(and_(*conditions))
        .order_by(MiniProgramQRCode.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_qrcode(
    db: AsyncSession,
    *,
    site_id: int,
    qrcode_id: int,
) -> Optional[MiniProgramQRCode]:
    """获取小程序码详情。"""
    result = await db.execute(
        select(MiniProgramQRCode).where(
            MiniProgramQRCode.id == qrcode_id,
            MiniProgramQRCode.site_id == site_id,
            MiniProgramQRCode.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def update_qrcode_status(
    db: AsyncSession,
    *,
    site_id: int,
    qrcode_id: int,
    status_value: str,
) -> MiniProgramQRCode:
    """启用或停用小程序码。"""
    qrcode = await get_qrcode(db, site_id=site_id, qrcode_id=qrcode_id)
    if not qrcode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QRCODE_NOT_FOUND", "message": "小程序码不存在"},
        )
    qrcode.status = status_value
    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(qrcode)
    return qrcode


async def regenerate_qrcode(
    db: AsyncSession,
    *,
    site_id: int,
    qrcode_id: int,
    generated_by: Optional[int] = None,
) -> MiniProgramQRCode:
    """重新请求微信接口生成图片，保留 scene 与短码。"""
    qrcode = await get_qrcode(db, site_id=site_id, qrcode_id=qrcode_id)
    if not qrcode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QRCODE_NOT_FOUND", "message": "小程序码不存在"},
        )
    qrcode.image_url = await _create_wechat_qrcode_image(
        site_id=site_id,
        scene=qrcode.scene,
        path=qrcode.path,
        target_type=qrcode.target_type,
    )
    archive_admin_id = generated_by or qrcode.generated_by
    if archive_admin_id and qrcode.image_url:
        await cms_service.register_existing_asset(
            db,
            site_id=site_id,
            file_url=qrcode.image_url,
            file_name=Path(qrcode.image_url).name,
            file_type="qrcode",
            admin_id=archive_admin_id,
        )
    qrcode.generated_at = datetime.now(timezone.utc)
    if generated_by:
        qrcode.generated_by = generated_by
    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(qrcode)
    return qrcode


async def create_temporary_order_qrcode_image(*, site_id: int, token: str) -> str:
    """为现场临时订单生成直达订单确认页的小程序码。"""
    access_token = await _get_wechat_access_token(site_id)
    payload = {
        "scene": token,
        "page": "pages/order-confirm/index",
        "check_path": False,
        "env_version": "release",
    }
    url = f"{WECHAT_API_BASE}/wxa/getwxacodeunlimit?access_token={access_token}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
    body = response.content
    validate_wechat_qrcode_image(
        content_type=response.headers.get("content-type", ""),
        body=body,
    )
    image_dir = TEMPORARY_QRCODE_IMAGE_DIR / str(site_id)
    image_dir.mkdir(parents=True, exist_ok=True)
    filename = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    image_path = image_dir / f"{filename}.png"
    image_path.write_bytes(body)
    return f"/images/qrcodes/temporary/{site_id}/{filename}.png"


async def resolve_qrcode(
    db: AsyncSession,
    *,
    site_id: int,
    scene: str,
    user_id: Optional[int] = None,
    openid: Optional[str] = None,
    client_info: Optional[dict[str, Any]] = None,
) -> QrcodeResolveResponse:
    """解析 scene，记录扫码日志并返回内部跳转路径。"""
    qrcode = await _find_qrcode_by_scene(db, site_id=site_id, scene=scene)
    if not qrcode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QRCODE_NOT_FOUND", "message": "小程序码不存在"},
        )
    if qrcode.status != "active":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "QRCODE_INACTIVE", "message": "小程序码已停用"},
        )

    now = datetime.now(timezone.utc)
    qrcode.usage_count = (qrcode.usage_count or 0) + 1
    qrcode.last_used_at = now
    db.add(
        MiniProgramQRCodeScanLog(
            site_id=site_id,
            qr_code_id=qrcode.id,
            user_id=user_id,
            openid=openid,
            channel=qrcode.channel,
            scanned_at=now,
            raw_scene=scene,
            client_info=client_info,
        )
    )
    await db.flush()
    return QrcodeResolveResponse(
        qr_code_id=qrcode.id,
        target_type=qrcode.target_type,
        target_key=qrcode.target_key,
        title=qrcode.title,
        path=qrcode.path,
        channel=qrcode.channel,
        status=qrcode.status,
        attribution_ttl_seconds=QRCODE_ATTRIBUTION_TTL_SECONDS,
    )


async def get_qrcode_image_path(
    db: AsyncSession,
    *,
    site_id: int,
    qrcode_id: int,
) -> Path:
    """返回本地小程序码图片路径。"""
    qrcode = await get_qrcode(db, site_id=site_id, qrcode_id=qrcode_id)
    if not qrcode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QRCODE_NOT_FOUND", "message": "小程序码不存在"},
        )
    if not qrcode.image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QRCODE_IMAGE_NOT_FOUND", "message": "小程序码图片不存在"},
        )
    relative_path = qrcode.image_url.removeprefix("/images/")
    image_path = Path(__file__).resolve().parents[1] / "images" / relative_path
    if not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QRCODE_IMAGE_NOT_FOUND", "message": "小程序码图片文件不存在"},
        )
    return image_path


async def get_transparent_qrcode_image_path(
    db: AsyncSession,
    *,
    site_id: int,
    qrcode_id: int,
) -> Path:
    """返回透明底 PNG 小程序码路径；保留原始二维码源文件不变。"""
    source_path = await get_qrcode_image_path(db, site_id=site_id, qrcode_id=qrcode_id)
    output_dir = TRANSPARENT_QRCODE_IMAGE_DIR / str(site_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / source_path.name
    if output_path.is_file() and output_path.stat().st_mtime >= source_path.stat().st_mtime:
        return output_path

    with Image.open(source_path) as image:
        rgba = image.convert("RGBA")
        pixels = []
        for red, green, blue, alpha in rgba.getdata():
            if red >= 248 and green >= 248 and blue >= 248:
                pixels.append((red, green, blue, 0))
            else:
                pixels.append((red, green, blue, alpha))
        rgba.putdata(pixels)
        rgba.save(output_path, format="PNG")
    return output_path


def get_wechat_mini_program_config(site_id: int) -> WechatMiniProgramConfig:
    """读取营地对应的小程序 AppID/Secret。"""
    app_id = settings.WECHAT_APP_ID
    app_secret = settings.WECHAT_APP_SECRET
    try:
        app_map = json.loads(settings.WECHAT_APPS or "{}")
        site_config = app_map.get(str(site_id)) or {}
        app_id = site_config.get("app_id") or app_id
        app_secret = site_config.get("app_secret") or app_secret
    except (TypeError, json.JSONDecodeError):
        pass
    if not app_id or not app_secret:
        raise QrcodeServiceError("微信小程序配置缺失: WECHAT_APP_ID/WECHAT_APP_SECRET")
    return WechatMiniProgramConfig(app_id=app_id, app_secret=app_secret)


def validate_wechat_qrcode_image(*, content_type: str, body: bytes) -> None:
    """校验微信接口返回的是非空图片。"""
    if not body:
        raise QrcodeServiceError("微信小程序码接口返回空图片")
    if not content_type.lower().startswith("image/"):
        raise QrcodeServiceError("微信小程序码接口未返回图片")


async def _validate_target_can_generate(
    db: AsyncSession,
    *,
    site_id: int,
    target_type: str,
    target_key: str,
) -> None:
    if target_type in {"custom_page", "activity_page"}:
        page = await cms_service.get_published_page(
            db,
            site_id=site_id,
            page_code=target_key,
        )
        if not page:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "CMS_PAGE_NOT_PUBLISHED", "message": "页面未发布，不能生成小程序码"},
            )


async def _find_existing_qrcode(
    db: AsyncSession,
    *,
    site_id: int,
    target_type: str,
    target_key: str,
    channel: str,
) -> Optional[MiniProgramQRCode]:
    result = await db.execute(
        select(MiniProgramQRCode).where(
            MiniProgramQRCode.site_id == site_id,
            MiniProgramQRCode.target_type == target_type,
            MiniProgramQRCode.target_key == target_key,
            MiniProgramQRCode.channel == channel,
            MiniProgramQRCode.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def _find_qrcode_by_scene(
    db: AsyncSession,
    *,
    site_id: int,
    scene: str,
) -> Optional[MiniProgramQRCode]:
    result = await db.execute(
        select(MiniProgramQRCode).where(
            MiniProgramQRCode.site_id == site_id,
            MiniProgramQRCode.scene == scene,
            MiniProgramQRCode.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


def _should_use_direct_path_qrcode(target_type: Optional[str], path: Optional[str]) -> bool:
    """商品码优先生成直达 path，避免依赖已发布小程序包含扫码 landing 页。"""
    return bool(path) and target_type in {"product", "activity_product"}


def _normalize_wechat_path(path: str) -> str:
    return path.lstrip("/")


async def _create_wechat_qrcode_image(
    *,
    site_id: int,
    scene: str,
    path: Optional[str] = None,
    target_type: Optional[str] = None,
) -> str:
    access_token = await _get_wechat_access_token(site_id)
    if _should_use_direct_path_qrcode(target_type, path):
        payload = {
            "path": _normalize_wechat_path(path or ""),
            "env_version": "release",
        }
        url = f"{WECHAT_API_BASE}/wxa/getwxacode?access_token={access_token}"
    else:
        payload = {
            "scene": scene,
            "page": "pages/qr/landing",
            "check_path": False,
            "env_version": "release",
        }
        url = f"{WECHAT_API_BASE}/wxa/getwxacodeunlimit?access_token={access_token}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
    body = response.content
    validate_wechat_qrcode_image(
        content_type=response.headers.get("content-type", ""),
        body=body,
    )
    image_dir = QRCODE_IMAGE_DIR / str(site_id)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / f"{scene}.png"
    image_path.write_bytes(body)
    return f"/images/qrcodes/{site_id}/{scene}.png"


async def _get_wechat_access_token(site_id: int) -> str:
    redis = get_redis()
    cache_key = f"wechat:access_token:{site_id}"
    cached = await redis.get(cache_key)
    if cached:
        return cached

    config = get_wechat_mini_program_config(site_id)
    url = (
        f"{WECHAT_API_BASE}/cgi-bin/token"
        f"?grant_type=client_credential&appid={config.app_id}&secret={config.app_secret}"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise QrcodeServiceError(f"微信 access_token 获取失败: {payload}")
    expires_in = int(payload.get("expires_in") or 7200)
    await redis.setex(cache_key, max(expires_in - 300, 60), access_token)
    return access_token


async def _generate_unique_short_code(db: AsyncSession) -> str:
    for _ in range(10):
        short_code = _generate_short_code()
        result = await db.execute(
            select(MiniProgramQRCode.id).where(MiniProgramQRCode.short_code == short_code)
        )
        if result.scalar_one_or_none() is None:
            return short_code
    raise QrcodeServiceError("小程序码短码生成失败")


def _generate_short_code(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
