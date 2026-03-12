"""
内容路由

- GET /faq/categories — FAQ 分类列表
- GET /faq/items — FAQ 搜索
- GET /disclaimers/{id} — 免责声明内容
- POST /disclaimers/sign — 签署免责声明
- GET /pages/{code} — 页面配置
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user, get_optional_user
from models.user import User
from schemas.common import ResponseModel
from schemas.user import DisclaimerSignRequest

router = APIRouter(prefix="/api/v1", tags=["内容"])


@router.get("/faq/categories", summary="FAQ 分类列表")
async def list_faq_categories(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取 FAQ 分类列表"""
    # TODO: content_service.list_faq_categories(db)
    return ResponseModel.success(data=[])


@router.get("/faq/items", summary="FAQ 搜索")
async def search_faq_items(
    category_id: Optional[int] = Query(None, description="分类ID"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """搜索 FAQ 问答列表"""
    # TODO: content_service.search_faq_items(db, category_id, keyword)
    return ResponseModel.success(data=[])


@router.get("/disclaimers/{disclaimer_id}", summary="免责声明内容")
async def get_disclaimer(
    disclaimer_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取免责声明模板内容"""
    # TODO: content_service.get_disclaimer(db, disclaimer_id)
    return ResponseModel.success(data={
        "id": disclaimer_id,
        "title": "",
        "content": "",
        "version": 1,
    })


@router.post("/disclaimers/sign", summary="签署免责声明")
async def sign_disclaimer(
    body: DisclaimerSignRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户签署免责声明"""
    # TODO: content_service.sign_disclaimer(db, user.id, body.order_id, body.template_id)
    return ResponseModel.success(data={"signed": True}, message="免责声明已签署")


@router.get("/pages/{page_code}", summary="页面配置")
async def get_page_config(
    page_code: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取页面配置（轮播图、活动banner等）"""
    # TODO: content_service.get_page_config(db, page_code)
    return ResponseModel.success(data={
        "code": page_code,
        "title": "",
        "components": [],
    })
