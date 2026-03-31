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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin, get_current_user
from middleware.site import get_site_id
from models.admin import AdminUser
from models.order import Ticket
from models.user import User
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.order import (
    MockPayRequest,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListParams,
    OrderResponse,
    PaymentRequest,
    RefundApproveRequest,
    RefundRequest,
    SeckillOrderCreateRequest,
    ShippingUpdateRequest,
    TicketResponse,
)
from services import order_service

router = APIRouter(tags=["订单"])


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
    )
    result = OrderResponse.model_validate(order)
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
    result = OrderResponse.model_validate(order)
    return ResponseModel.success(data=result, message="订单已取消")


@router.post("/api/v1/orders/{order_id}/refund", summary="申请退票")
async def apply_refund(
    order_id: int,
    body: RefundRequest = RefundRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """申请退票（仅限已支付/已验票状态）"""
    order = await order_service.apply_refund(
        db, order_id, user.id,
        reason=body.reason,
        order_item_ids=body.order_item_ids,
    )
    result = OrderResponse.model_validate(order)
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
    result = OrderResponse.model_validate(order)
    return ResponseModel.success(data=result, message="模拟支付完成")


@router.get("/api/v1/orders/{order_id}/tickets", summary="获取电子票")
async def get_order_tickets(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取订单关联的电子票列表"""
    # 先校验订单归属
    await order_service.get_order_detail(db, order_id, user_id=user.id)

    # 查询该订单的电子票
    result = await db.execute(
        select(Ticket).where(
            Ticket.order_id == order_id,
            Ticket.user_id == user.id,
            Ticket.is_deleted.is_(False),
        )
    )
    tickets = list(result.scalars().all())
    items = [TicketResponse.model_validate(t) for t in tickets]
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
        identity_ids=body.identity_ids,
        disclaimer_signed=body.disclaimer_signed,
    )
    result = OrderResponse.model_validate(order)
    return ResponseModel.success(data=result, message="秒杀下单成功")


# ========== B端管理接口 ==========

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
    """管理端审批退款：通过则发起退款并释放库存，拒绝则恢复已支付状态"""
    # 校验订单属于当前营地
    site_id = get_site_id(request)
    order_check = await order_service.get_order_detail(db, order_id)
    if order_check.site_id != site_id:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})
    order = await order_service.approve_refund(
        db, order_id,
        approved=body.approved,
        reject_reason=body.reject_reason,
        operator_id=admin.id,
    )
    result = OrderResponse.model_validate(order)
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
    order_check = await order_service.get_order_detail(db, order_id)
    if order_check.site_id != site_id:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})
    order = await order_service.update_shipping(
        db, order_id,
        shipping_no=body.shipping_no,
        shipping_company=body.shipping_company,
        operator_id=admin.id,
    )
    result = OrderResponse.model_validate(order)
    return ResponseModel.success(data=result, message="物流信息已更新")
