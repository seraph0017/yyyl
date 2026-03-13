"""
内容路由

- GET /faq/categories — FAQ 分类列表
- GET /faq/items — FAQ 搜索
- GET /disclaimers/{id} — 免责声明内容
- POST /disclaimers/sign — 签署免责声明
- GET /pages/{code} — 页面配置
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user, get_optional_user
from models.content import (
    DisclaimerSignature,
    DisclaimerTemplate,
    FaqCategory,
    FaqItem,
    PageConfig,
)
from models.user import User
from schemas.common import ResponseModel
from schemas.user import DisclaimerSignRequest

router = APIRouter(prefix="/api/v1", tags=["内容"])


@router.get("/faq/categories", summary="FAQ 分类列表")
async def list_faq_categories(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取 FAQ 分类列表（含分类下的条目）"""
    result = await db.execute(
        select(FaqCategory)
        .where(FaqCategory.is_deleted.is_(False))
        .order_by(FaqCategory.sort_order.asc())
    )
    categories = result.scalars().all()

    data = []
    for cat in categories:
        # items 通过 selectin 关系自动加载
        active_items = [
            {
                "id": item.id,
                "question": item.question,
                "answer": item.answer,
                "keywords": item.keywords,
                "sort_order": item.sort_order,
                "click_count": item.click_count,
            }
            for item in (cat.items or [])
            if item.status == "active" and not item.is_deleted
        ]
        # 按 sort_order 排序
        active_items.sort(key=lambda x: x["sort_order"])

        data.append({
            "id": cat.id,
            "name": cat.name,
            "code": cat.code,
            "sort_order": cat.sort_order,
            "items": active_items,
        })

    return ResponseModel.success(data=data)


@router.get("/faq/items", summary="FAQ 搜索")
async def search_faq_items(
    category_id: Optional[int] = Query(None, description="分类ID"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """搜索 FAQ 问答列表"""
    conditions = [
        FaqItem.status == "active",
        FaqItem.is_deleted.is_(False),
    ]

    if category_id is not None:
        conditions.append(FaqItem.category_id == category_id)

    if keyword:
        keyword_pattern = f"%{keyword}%"
        conditions.append(
            or_(
                FaqItem.question.ilike(keyword_pattern),
                FaqItem.answer.ilike(keyword_pattern),
                # JSONB 数组包含关键词：使用 @> 操作符
                FaqItem.keywords.op("@>")(f'["{keyword}"]'),
            )
        )

    result = await db.execute(
        select(FaqItem)
        .where(*conditions)
        .order_by(FaqItem.sort_order.asc())
    )
    items = result.scalars().all()

    data = [
        {
            "id": item.id,
            "category_id": item.category_id,
            "question": item.question,
            "answer": item.answer,
            "keywords": item.keywords,
            "sort_order": item.sort_order,
            "click_count": item.click_count,
        }
        for item in items
    ]

    return ResponseModel.success(data=data)


@router.get("/disclaimers/{disclaimer_id}", summary="免责声明内容")
async def get_disclaimer(
    disclaimer_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取免责声明模板内容"""
    result = await db.execute(
        select(DisclaimerTemplate).where(
            DisclaimerTemplate.id == disclaimer_id,
            DisclaimerTemplate.is_deleted.is_(False),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "免责声明不存在"},
        )

    return ResponseModel.success(data={
        "id": template.id,
        "title": template.title,
        "content": template.content,
        "version": template.version,
        "content_hash": template.content_hash,
    })


@router.post("/disclaimers/sign", summary="签署免责声明")
async def sign_disclaimer(
    body: DisclaimerSignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户签署免责声明"""
    # 查询模板获取 content_hash
    result = await db.execute(
        select(DisclaimerTemplate).where(
            DisclaimerTemplate.id == body.template_id,
            DisclaimerTemplate.is_deleted.is_(False),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "免责声明模板不存在"},
        )

    # 获取客户端 IP
    client_ip = request.client.host if request.client else None

    # 创建签署记录
    signature = DisclaimerSignature(
        user_id=user.id,
        template_id=body.template_id,
        order_id=body.order_id,
        content_hash=template.content_hash,
        signed_at=datetime.now(timezone.utc),
        signer_openid=user.openid,
        signer_ip=client_ip,
    )
    db.add(signature)
    await db.commit()

    return ResponseModel.success(data={"signed": True}, message="免责声明已签署")


@router.get("/pages/{page_code}", summary="页面配置")
async def get_page_config(
    page_code: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取页面配置（轮播图、活动banner等）"""
    result = await db.execute(
        select(PageConfig).where(
            PageConfig.page_key == page_code,
            PageConfig.status == "active",
            PageConfig.is_deleted.is_(False),
        )
    )
    page_config = result.scalar_one_or_none()
    if not page_config:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "页面配置不存在"},
        )

    return ResponseModel.success(data=page_config.config_data)
