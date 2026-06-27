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
from middleware.site import get_site_id
from models.content import (
    DisclaimerSignature,
    DisclaimerTemplate,
    FaqCategory,
    FaqItem,
    PageConfig,
)
from models.customer_service import CustomerServiceAskLog, CustomerServiceKnowledgeArticle
from models.user import User
from schemas.common import ResponseModel
from schemas.user import DisclaimerSignRequest
from services.customer_service_knowledge_service import (
    build_ask_log_payload,
    build_feedback_token,
    select_knowledge_answer,
    verify_feedback_token,
)

router = APIRouter(prefix="/api/v1", tags=["内容"])


@router.get("/faq/categories", summary="FAQ 分类列表")
async def list_faq_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取 FAQ 分类列表（含分类下的条目）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(FaqCategory)
        .where(FaqCategory.is_deleted.is_(False), FaqCategory.site_id == site_id)
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
    request: Request,
    category_id: Optional[int] = Query(None, description="分类ID"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """搜索 FAQ 问答列表"""
    site_id = get_site_id(request)
    conditions = [
        FaqItem.status == "active",
        FaqItem.is_deleted.is_(False),
        FaqItem.site_id == site_id,
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


@router.post("/customer-service/ask", summary="智能客服知识库问答")
async def ask_customer_service(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """小程序智能客服问答：只基于当前营地已发布知识库回答。"""
    site_id = get_site_id(request)
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "请输入问题"},
        )
    if len(question) > 300:
        raise HTTPException(
            status_code=400,
            detail={"code": 40002, "message": "问题不能超过300字"},
        )

    result = await db.execute(
        select(CustomerServiceKnowledgeArticle).where(
            CustomerServiceKnowledgeArticle.site_id == site_id,
            CustomerServiceKnowledgeArticle.status == "published",
            CustomerServiceKnowledgeArticle.is_deleted.is_(False),
        )
    )
    articles = result.scalars().all()
    answer = select_knowledge_answer(question=question, articles=articles, site_id=site_id)

    log = CustomerServiceAskLog(
        **build_ask_log_payload(
            site_id=site_id,
            channel="miniapp",
            question=question,
            result=answer,
            user_id=user.id if user else None,
        )
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return ResponseModel.success(data={
        **answer,
        "log_id": log.id,
        "feedback_token": build_feedback_token(
            log_id=log.id,
            site_id=site_id,
            user_id=user.id if user else None,
        ),
    })


@router.post("/customer-service/ask-logs/{log_id}/feedback", summary="智能客服回答反馈")
async def submit_customer_service_feedback(
    log_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """记录智能客服回答是否有帮助。"""
    site_id = get_site_id(request)
    feedback = (body.get("feedback") or "").strip()
    comment = (body.get("comment") or "").strip()
    if feedback not in {"helpful", "unhelpful"}:
        raise HTTPException(
            status_code=400,
            detail={"code": 40003, "message": "反馈类型不支持"},
        )
    feedback_token = (body.get("feedback_token") or "").strip()
    if not verify_feedback_token(
        feedback_token,
        log_id=log_id,
        site_id=site_id,
        user_id=user.id if user else None,
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": 40303, "message": "feedback_token 无效或已不匹配"},
        )

    conditions = [
        CustomerServiceAskLog.id == log_id,
        CustomerServiceAskLog.site_id == site_id,
        CustomerServiceAskLog.is_deleted.is_(False),
    ]
    if user:
        conditions.append(
            or_(
                CustomerServiceAskLog.user_id == user.id,
                CustomerServiceAskLog.user_id.is_(None),
            )
        )

    result = await db.execute(select(CustomerServiceAskLog).where(*conditions))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "问答记录不存在"},
        )
    if log.feedback:
        raise HTTPException(
            status_code=409,
            detail={"code": 40901, "message": "该回答已提交过反馈"},
        )
    log.feedback = feedback
    log.feedback_comment = comment[:500] if comment else None
    await db.commit()
    return ResponseModel.success(message="反馈已记录")


@router.get("/disclaimers/{disclaimer_id}", summary="免责声明内容")
async def get_disclaimer(
    disclaimer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取免责声明模板内容"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(DisclaimerTemplate).where(
            DisclaimerTemplate.id == disclaimer_id,
            DisclaimerTemplate.is_deleted.is_(False),
            DisclaimerTemplate.site_id == site_id,
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取页面配置（轮播图、活动banner等）"""
    site_id = get_site_id(request)
    result = await db.execute(
        select(PageConfig).where(
            PageConfig.page_key == page_code,
            PageConfig.status == "active",
            PageConfig.is_deleted.is_(False),
            PageConfig.site_id == site_id,
        )
    )
    page_config = result.scalar_one_or_none()
    if not page_config:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "页面配置不存在"},
        )

    return ResponseModel.success(data=page_config.config_data)
