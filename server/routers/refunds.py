"""
v1.7 退款路由
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from schemas.common import PaginatedResponse, ResponseModel
from schemas.refund import (
    RefundApproveRequest,
    RefundCreateRequest,
    RefundRecordResponse,
    RefundRejectRequest,
)
from services import refund_service

router = APIRouter(prefix="/api/v1", tags=["退款"])


@router.post("/admin/orders/{order_id}/refunds", summary="创建退款操作")
async def create_refund(
    order_id: int,
    body: RefundCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    order = await refund_service.get_order_for_refund(db, order_id=order_id, site_id=site_id)
    refund = await refund_service.create_refund_record(
        db,
        order,
        refund_mode=body.refund_mode,
        order_action=body.order_action,
        refund_amount=body.refund_amount,
        release_inventory=body.release_inventory,
        reason=body.reason,
        requested_by=admin.id,
        requester_role=admin.role.role_code if admin.role else "admin",
        items=[item.model_dump() for item in body.items] if body.items else None,
    )
    return ResponseModel.success(
        data=RefundRecordResponse.model_validate(refund).model_dump(mode="json"),
        message="退款记录已创建",
    )


@router.get("/admin/orders/{order_id}/refunds", summary="订单退款记录")
async def list_order_refunds(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    refunds, _ = await refund_service.list_refunds(db, site_id=site_id, order_id=order_id)
    return ResponseModel.success(
        data=[RefundRecordResponse.model_validate(item).model_dump(mode="json") for item in refunds]
    )


@router.get("/admin/refunds", summary="退款记录列表")
async def list_refunds(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    refunds, total = await refund_service.list_refunds(
        db,
        site_id=site_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(
        items=[RefundRecordResponse.model_validate(item).model_dump(mode="json") for item in refunds],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/refunds/{refund_id}", summary="退款详情")
async def get_refund_detail(
    refund_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    refund = await refund_service.get_refund_detail(db, site_id=site_id, refund_id=refund_id)
    return ResponseModel.success(data=RefundRecordResponse.model_validate(refund).model_dump(mode="json"))


@router.post("/admin/refunds/{refund_id}/approve", summary="审批通过退款")
async def approve_refund(
    refund_id: int,
    body: RefundApproveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    refund = await refund_service.approve_refund(
        db,
        refund_id=refund_id,
        site_id=site_id,
        approved_by=admin.id,
    )
    return ResponseModel.success(data=RefundRecordResponse.model_validate(refund).model_dump(mode="json"))


@router.post("/admin/refunds/{refund_id}/reject", summary="拒绝退款")
async def reject_refund(
    refund_id: int,
    body: RefundRejectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    refund = await refund_service.reject_refund(
        db,
        refund_id=refund_id,
        site_id=site_id,
        rejected_by=admin.id,
        reason=body.reason,
    )
    return ResponseModel.success(data=RefundRecordResponse.model_validate(refund).model_dump(mode="json"))
