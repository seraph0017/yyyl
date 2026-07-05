"""
订单路由

C端 /api/v1/orders：
- POST / — 创建订单
- GET / — 订单列表
- GET /{id} — 订单详情
- POST /{id}/cancel — 取消订单
- POST /{id}/refund — 申请退票
- POST /{id}/pay — 发起支付
- POST /{id}/mock-pay — 模拟支付
- GET /{id}/tickets — 获取电子票
- POST /seckill — 秒杀下单

B端 /api/v1/admin/orders：
- GET / — 管理端订单列表
- POST /{id}/refund-approve — 审批退款
- PUT /{id}/shipping — 更新物流
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin, get_current_staff_principal, get_current_user
from middleware.site import get_site_id
from models.admin import AdminUser
from models.order import Ticket
from models.user import User
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.order_export import OrderExportCreateRequest, OrderExportTaskResponse
from schemas.order import (
    MockPayRequest,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListParams,
    OrderQuoteRequest,
    OrderQuoteResponse,
    OrderResponse,
    PaymentRequest,
    RefundApproveRequest,
    RefundRequest,
    SeckillOrderCreateRequest,
    ShippingUpdateRequest,
    TemporaryOrderClaimResponse,
    TemporaryOrderCodePayResponse,
    TemporaryOrderCreateRequest,
    TemporaryOrderSessionResponse,
    TicketResponse,
)
from services import order_service, refund_service
from services import order_export_service
from services import ticket_service

router = APIRouter(tags=["订单"])


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


# ========== C端接口 ==========

@router.post("/api/v1/orders", summary="创建订单")
async def create_order(
    body: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建普通订单：校验商品→锁库存→计算价格→创建订单→生成电子票"""
    items_data = [item.model_dump() for item in body.items]
    order = await order_service.create_order(
        db,
        user,
        items_data,
        disclaimer_signed=body.disclaimer_signed,
        disclaimer_template_id=body.disclaimer_template_id,
        address_id=body.address_id,
        remark=body.remark,
        payment_method=body.payment_method,
        times_card_id=body.times_card_id,
        source_qrcode_id=body.source_qrcode_id,
        source_channel=body.source_channel,
        source_scanned_at=body.source_scanned_at,
    )
    order_detail = await order_service.get_order_detail(db, order.id, user_id=user.id)
    result = OrderResponse.model_validate(order_detail)
    return ResponseModel.success(data=result, message="订单创建成功")


@router.get("/api/v1/orders", summary="我的订单列表")
async def list_orders(
    params: OrderListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C端用户订单列表，支持状态/类型/日期筛选"""
    orders, total = await order_service.list_orders(
        db,
        user_id=user.id,
        order_status=params.status,
        order_type=params.order_type,
        date_start=params.date_start,
        date_end=params.date_end,
        keyword=params.keyword,
        payment_status=params.payment_status,
        product_id=params.product_id,
        sku_id=params.sku_id,
        product_type=params.product_type,
        booking_date_start=params.booking_date_start,
        booking_date_end=params.booking_date_end,
        time_slot=params.time_slot,
        payment_time_start=params.payment_time_start,
        payment_time_end=params.payment_time_end,
        amount_min=params.amount_min,
        amount_max=params.amount_max,
        verify_status=params.verify_status,
        source_channel=params.source_channel,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [OrderResponse.model_validate(o) for o in orders]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/api/v1/orders/quote", summary="订单报价与库存预校验")
async def quote_order(
    body: OrderQuoteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """订单确认页报价：校验商品、价格、库存与优惠，不锁库存、不创建订单。"""
    items_data = [item.model_dump() for item in body.items]
    quote = await order_service.quote_order(
        db,
        user,
        items_data,
        disclaimer_signed=body.disclaimer_signed,
    )
    result = OrderQuoteResponse.model_validate(quote)
    return ResponseModel.success(data=result)


@router.post("/api/v1/orders/temporary/{token}/claim", summary="认领现场临时订单")
async def claim_temporary_order(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """顾客扫码后将现场临时会话转成自己的正式订单。"""
    site_id = get_site_id(request)
    order = await order_service.claim_temporary_order_session(
        db,
        site_id=site_id,
        token=token,
        user=user,
    )
    order_detail = await order_service.get_order_detail(db, order.id, user_id=user.id)
    result = TemporaryOrderClaimResponse.model_validate({
        "order": OrderResponse.model_validate(order_detail),
        "payment_params": None,
    })
    return ResponseModel.success(data=result, message="临时订单已生成")


@router.get("/api/v1/orders/{order_id}", summary="订单详情")
async def get_order_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C端获取订单详情（含订单项列表）"""
    order = await order_service.get_order_detail(db, order_id, user_id=user.id)
    result = OrderResponse.model_validate(order)
    return ResponseModel.success(data=result)


@router.post("/api/v1/orders/{order_id}/cancel", summary="取消订单")
async def cancel_order(
    order_id: int,
    body: OrderCancelRequest = OrderCancelRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """取消订单（仅限待支付状态），释放锁定的库存"""
    order = await order_service.cancel_order(
        db, order_id, user.id, reason=body.reason,
    )
    order_detail = await order_service.get_order_detail(db, order.id, user_id=user.id)
    result = OrderResponse.model_validate(order_detail)
    return ResponseModel.success(data=result, message="订单已取消")


@router.post("/api/v1/orders/{order_id}/refund", summary="申请退票")
async def apply_refund(
    order_id: int,
    body: RefundRequest = RefundRequest(),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """申请退票（仅限已支付/已验票状态）"""
    site_id = get_site_id(request) if request is not None else 1
    order = await refund_service.get_order_for_refund(db, order_id=order_id, site_id=site_id)
    if order.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})

    refund_items = None
    refund_amount = order.actual_amount
    refund_mode = "full"
    order_action = "cancel_order"
    if body.order_item_ids:
        selected_ids = set(body.order_item_ids)
        selected_items = [item for item in order.items if item.id in selected_ids]
        if len(selected_items) != len(selected_ids):
            raise HTTPException(status_code=400, detail={"code": 40042, "message": "退款明细包含不存在的订单项"})
        refund_mode = "item"
        order_action = "keep_order"
        refund_amount = sum((item.actual_price for item in selected_items), Decimal("0.00"))
        refund_items = [
            {
                "order_item_id": item.id,
                "refund_amount": item.actual_price,
                "quantity": item.quantity,
            }
            for item in selected_items
        ]

    await refund_service.create_refund_record(
        db,
        order,
        refund_mode=refund_mode,
        order_action=order_action,
        refund_amount=refund_amount,
        release_inventory=True,
        reason=body.reason or "用户申请退票",
        requested_by=user.id,
        requester_role="user",
        items=refund_items,
    )
    order_detail = await order_service.get_order_detail(db, order.id, user_id=user.id)
    result = OrderResponse.model_validate(order_detail)
    return ResponseModel.success(data=result, message="退票申请已提交")


@router.post("/api/v1/orders/{order_id}/pay", summary="发起支付")
async def initiate_payment(
    order_id: int,
    body: PaymentRequest = PaymentRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发起微信支付，返回小程序调起支付的参数"""
    result = await order_service.initiate_payment(
        db, order_id, user.id, payment_method=body.payment_method,
    )
    return ResponseModel.success(data=result)


@router.post("/api/v1/orders/{order_id}/mock-pay", summary="模拟支付")
async def mock_pay_order(
    order_id: int,
    body: MockPayRequest = MockPayRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """开发/测试环境模拟支付，直接将订单状态变更为已支付并生成电子票"""
    order = await order_service.mock_pay_order(
        db, order_id, user.id, success=body.success,
    )
    order_detail = await order_service.get_order_detail(db, order.id, user_id=user.id)
    result = OrderResponse.model_validate(order_detail)
    return ResponseModel.success(data=result, message="模拟支付完成")


@router.get("/api/v1/orders/{order_id}/tickets", summary="获取电子票")
async def get_order_tickets(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取订单关联的电子票列表"""
    site_id = get_site_id(request)
    # 先校验订单归属
    await order_service.get_order_detail(db, order_id, user_id=user.id, site_id=site_id)

    # 查询该订单的电子票
    result = await db.execute(
        select(Ticket).where(
            Ticket.order_id == order_id,
            Ticket.site_id == site_id,
            Ticket.user_id == user.id,
            Ticket.is_deleted.is_(False),
        )
    )
    tickets = list(result.scalars().all())
    items = [
        TicketResponse.model_validate(await ticket_service.build_ticket_response(db, ticket))
        for ticket in tickets
    ]
    await db.commit()
    return ResponseModel.success(data=items)


@router.post("/api/v1/orders/seckill", summary="秒杀下单")
async def seckill_order(
    body: SeckillOrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """秒杀下单：Redis 预扣库存 → 创建订单"""
    order = await order_service.seckill_order(
        db,
        user,
        product_id=body.product_id,
        booking_date=body.booking_date,
        quantity=body.quantity,
        sku_id=body.sku_id,
        time_slot=getattr(body, "time_slot", None),
        identity_ids=body.identity_ids,
        disclaimer_signed=body.disclaimer_signed,
    )
    order_detail = await order_service.get_order_detail(db, order.id, user_id=user.id)
    result = OrderResponse.model_validate(order_detail)
    return ResponseModel.success(data=result, message="秒杀下单成功")


# ========== B端管理接口 ==========

@router.post("/api/v1/admin/orders/temporary", summary="管理端创建现场临时订单/收款")
async def admin_create_temporary_order(
    body: TemporaryOrderCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理后台创建现场临时订单；付款码模式会立即调用微信付款码接口。"""
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    session, token = await order_service.create_temporary_order_session(
        db,
        site_id=site_id,
        body=body,
        operator_id=admin.id,
        operator_source="admin",
    )
    if body.payment_flow == "merchant_scan_code":
        order, pay_result = await order_service.charge_temporary_order_by_auth_code(
            db,
            site_id=site_id,
            session=session,
            auth_code=body.auth_code or "",
            device_id=body.device_id,
        )
        order_detail = await order_service.get_order_detail(db, order.id)
        result = TemporaryOrderCodePayResponse.model_validate({
            "session": TemporaryOrderSessionResponse.model_validate(
                order_service.build_temporary_session_response_payload(session)
            ),
            "order": OrderResponse.model_validate(order_detail),
            "trade_state": pay_result.get("trade_state"),
            "transaction_id": pay_result.get("transaction_id"),
            "requires_query": bool(pay_result.get("requires_query")),
        })
        return ResponseModel.success(data=result, message="付款码收款已提交微信处理")

    result = TemporaryOrderSessionResponse.model_validate(
        order_service.build_temporary_session_response_payload(session, token=token)
    )
    return ResponseModel.success(data=result, message="现场临时订单已创建")


@router.post("/api/v1/admin/orders/temporary/{session_id}/query-codepay", summary="管理端查询现场付款码收款结果")
async def admin_query_temporary_codepay(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理后台对微信付款码未知态/用户输密态执行查单补偿。"""
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    session, order, pay_result = await order_service.query_temporary_codepay_result(
        db,
        site_id=site_id,
        session_id=session_id,
        operator_id=admin.id,
        operator_source="admin",
    )
    order_detail = await order_service.get_order_detail(db, order.id)
    result = TemporaryOrderCodePayResponse.model_validate({
        "session": TemporaryOrderSessionResponse.model_validate(
            order_service.build_temporary_session_response_payload(session)
        ),
        "order": OrderResponse.model_validate(order_detail),
        "trade_state": pay_result.get("trade_state"),
        "transaction_id": pay_result.get("transaction_id"),
        "requires_query": bool(pay_result.get("requires_query")),
    })
    return ResponseModel.success(data=result, message="付款码查单完成")


@router.post("/api/v1/staff/orders/temporary", summary="员工端创建现场临时订单/收款")
async def staff_create_temporary_order(
    body: TemporaryOrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """员工小程序创建现场临时订单；付款码模式会立即调用微信付款码接口。"""
    session, token = await order_service.create_temporary_order_session(
        db,
        site_id=staff.site_id,
        body=body,
        operator_id=staff.id,
        operator_source=staff.source,
    )
    if body.payment_flow == "merchant_scan_code":
        order, pay_result = await order_service.charge_temporary_order_by_auth_code(
            db,
            site_id=staff.site_id,
            session=session,
            auth_code=body.auth_code or "",
            device_id=body.device_id,
        )
        order_detail = await order_service.get_order_detail(db, order.id)
        result = TemporaryOrderCodePayResponse.model_validate({
            "session": TemporaryOrderSessionResponse.model_validate(
                order_service.build_temporary_session_response_payload(session)
            ),
            "order": OrderResponse.model_validate(order_detail),
            "trade_state": pay_result.get("trade_state"),
            "transaction_id": pay_result.get("transaction_id"),
            "requires_query": bool(pay_result.get("requires_query")),
        })
        return ResponseModel.success(data=result, message="付款码收款已提交微信处理")

    result = TemporaryOrderSessionResponse.model_validate(
        order_service.build_temporary_session_response_payload(session, token=token)
    )
    return ResponseModel.success(data=result, message="现场临时订单已创建")


@router.post("/api/v1/staff/orders/temporary/{session_id}/query-codepay", summary="员工端查询现场付款码收款结果")
async def staff_query_temporary_codepay(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    staff = Depends(get_current_staff_principal),
):
    """员工端对微信付款码未知态/用户输密态执行查单补偿。"""
    session, order, pay_result = await order_service.query_temporary_codepay_result(
        db,
        site_id=staff.site_id,
        session_id=session_id,
        operator_id=staff.id,
        operator_source=staff.source,
    )
    order_detail = await order_service.get_order_detail(db, order.id)
    result = TemporaryOrderCodePayResponse.model_validate({
        "session": TemporaryOrderSessionResponse.model_validate(
            order_service.build_temporary_session_response_payload(session)
        ),
        "order": OrderResponse.model_validate(order_detail),
        "trade_state": pay_result.get("trade_state"),
        "transaction_id": pay_result.get("transaction_id"),
        "requires_query": bool(pay_result.get("requires_query")),
    })
    return ResponseModel.success(data=result, message="付款码查单完成")


@router.get("/api/v1/admin/orders", summary="管理端订单列表")
async def admin_list_orders(
    request: Request,
    params: OrderListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端订单列表，可查看所有用户的订单"""
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    orders, total = await order_service.list_orders(
        db,
        site_id=site_id,
        user_id=params.user_id,
        order_status=params.status,
        order_type=params.order_type,
        date_start=params.date_start,
        date_end=params.date_end,
        keyword=params.keyword,
        payment_status=params.payment_status,
        product_id=params.product_id,
        sku_id=params.sku_id,
        product_type=params.product_type,
        booking_date_start=params.booking_date_start,
        booking_date_end=params.booking_date_end,
        time_slot=params.time_slot,
        payment_time_start=params.payment_time_start,
        payment_time_end=params.payment_time_end,
        amount_min=params.amount_min,
        amount_max=params.amount_max,
        verify_status=params.verify_status,
        source_channel=params.source_channel,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [OrderResponse.model_validate(o) for o in orders]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/api/v1/admin/orders/{order_id}/refund-approve", summary="审批退款")
async def approve_refund(
    order_id: int,
    body: RefundApproveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端兼容退款审批：统一走 RefundRecord 状态机。"""
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    if not admin.role or admin.role.role_code != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": 40301, "message": "仅超级管理员可审批退款"},
        )
    order = await refund_service.get_order_for_refund(db, order_id=order_id, site_id=site_id)
    if order.site_id != site_id:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})

    refund = await refund_service.find_pending_refund_for_order(
        db,
        order_id=order_id,
        site_id=site_id,
    )
    if refund is None:
        refund = await refund_service.create_refund_record(
            db,
            order,
            refund_mode="full",
            order_action="cancel_order",
            refund_amount=order.actual_amount,
            release_inventory=True,
            reason=order.remark or "兼容订单退款审批",
            requested_by=admin.id,
            requester_role=admin.role.role_code if admin.role else "admin",
        )

    if body.approved:
        if refund.status == "pending":
            await refund_service.approve_refund(db, refund_id=refund.id, site_id=site_id, approved_by=admin.id)
    else:
        await refund_service.reject_refund(
            db,
            refund_id=refund.id,
            site_id=site_id,
            rejected_by=admin.id,
            reason=body.reject_reason or "退款审批拒绝",
        )
    order_detail = await order_service.get_order_detail(db, order_id)
    result = OrderResponse.model_validate(order_detail)
    message = "退款已通过" if body.approved else "退款已拒绝"
    return ResponseModel.success(data=result, message=message)


@router.put("/api/v1/admin/orders/{order_id}/shipping", summary="更新物流")
async def update_shipping(
    order_id: int,
    body: ShippingUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """管理端更新订单物流信息"""
    # 校验订单属于当前营地
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    order_check = await order_service.get_order_detail(db, order_id)
    if order_check.site_id != site_id:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})
    order = await order_service.update_shipping(
        db, order_id,
        shipping_no=body.shipping_no,
        shipping_company=body.shipping_company,
        operator_id=admin.id,
    )
    order_detail = await order_service.get_order_detail(db, order.id)
    result = OrderResponse.model_validate(order_detail)
    return ResponseModel.success(data=result, message="物流信息已更新")


@router.post("/api/v1/admin/orders/export", summary="创建订单导出任务")
async def create_order_export(
    body: OrderExportCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建订单导出任务。"""
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    task = await order_export_service.create_order_export_task(
        db,
        site_id=site_id,
        filters=body.filters,
        file_format=body.file_format,
        include_sensitive=body.include_sensitive,
        created_by=admin.id,
    )
    return ResponseModel.success(
        data=OrderExportTaskResponse.model_validate(task).model_dump(mode="json"),
        message="订单导出任务已创建",
    )


@router.get("/api/v1/admin/orders/export-tasks", summary="订单导出任务列表")
async def list_order_export_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    tasks, total = await order_export_service.list_export_tasks(
        db,
        site_id=site_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(
        items=[OrderExportTaskResponse.model_validate(task).model_dump(mode="json") for task in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api/v1/admin/orders/export-tasks/{task_id}", summary="订单导出任务详情")
async def get_order_export_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    task = await order_export_service.get_export_task(db, site_id=site_id, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"code": "ORDER_EXPORT_NOT_FOUND", "message": "导出任务不存在"})
    return ResponseModel.success(data=OrderExportTaskResponse.model_validate(task).model_dump(mode="json"))


@router.get("/api/v1/admin/orders/export-tasks/{task_id}/download", summary="下载订单导出文件")
async def download_order_export_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    file_path = await order_export_service.get_export_download_path(db, site_id=site_id, task_id=task_id)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="text/csv",
    )


@router.post("/api/v1/admin/orders/{order_id}/settle", summary="手动触发订单结算")
async def settle_order(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    site_id = get_site_id(request)
    _ensure_admin_site_access(admin, site_id)
    if not admin.role or admin.role.role_code != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={"code": 40301, "message": "仅超级管理员可手动触发结算"},
        )
    order = await order_service.get_order_detail(db, order_id)
    if order.site_id != site_id:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})
    settlement = await order_service.settle_completed_order(db, order, trigger_type="manual")
    return ResponseModel.success(
        data={
            "site_id": site_id,
            "order_id": order_id,
            "status": settlement.status,
            "amount": str(settlement.amount),
            "settlement_no": settlement.settlement_no,
        },
        message="订单结算已完成",
    )
