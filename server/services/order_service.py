"""
订单服务

- create_order：创建订单（校验→锁库存→计算价格→创建订单→生成电子票）
- cancel_order：取消订单
- apply_refund：申请退票
- mock_pay_order：模拟支付
- initiate_payment：发起微信支付
- seckill_order：秒杀下单
- get_order_detail：获取订单详情
- list_orders：订单列表
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.order import Order, OrderItem, Ticket
from models.product import DateTypeConfig, DiscountRule, Inventory, PricingRule, Product
from models.user import User
from redis_client import get_redis
from services import inventory_service
from utils.helpers import generate_order_no, generate_qr_token, generate_ticket_code

logger = logging.getLogger(__name__)

# 排序字段白名单
ALLOWED_SORT_FIELDS = {"id", "created_at", "actual_amount", "status"}


async def create_order(
    db: AsyncSession,
    user: User,
    items_data: List[Dict[str, Any]],
    *,
    disclaimer_signed: bool = False,
    disclaimer_template_id: Optional[int] = None,
    address_id: Optional[int] = None,
    remark: Optional[str] = None,
    payment_method: str = "wechat_pay",
    times_card_id: Optional[int] = None,
) -> Order:
    """创建普通订单

    完整流程：校验商品→锁库存→计算价格→创建订单→生成电子票

    Args:
        db: 数据库会话
        user: 当前用户
        items_data: 订单项数据列表
        disclaimer_signed: 是否已签免责声明
        disclaimer_template_id: 免责模板ID
        address_id: 收货地址ID
        remark: 备注
        payment_method: 支付方式
        times_card_id: 次数卡ID

    Returns:
        创建的 Order 实例

    Raises:
        HTTPException: 各种业务校验失败
    """
    total_amount = Decimal("0")
    discount_amount = Decimal("0")
    deposit_amount = Decimal("0")
    order_type = ""
    order_items: List[Dict[str, Any]] = []
    locked_inventories: List[Tuple[int, Any, int, Any, Any]] = []  # 记录已锁定的库存，异常时回滚

    try:
        for item_data in items_data:
            product_id = item_data["product_id"]
            sku_id = item_data.get("sku_id")
            quantity = item_data.get("quantity", 1)
            dates = item_data.get("dates", [])
            time_slot = item_data.get("time_slot")
            identity_ids = item_data.get("identity_ids", [])

            # 1. 查询并校验商品
            result = await db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.is_deleted.is_(False),
                    Product.status == "on_sale",
                )
            )
            product = result.scalar_one_or_none()
            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": 40401, "message": f"商品不存在或已下架: id={product_id}"},
                )

            # 确定订单类型（取第一个商品类型）
            if not order_type:
                order_type = product.type

            # 2. 校验免责声明
            if product.require_disclaimer and not disclaimer_signed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": 40915, "message": "请先签署免责声明"},
                )

            # 3. 开票时间校验
            if product.sale_start_at and datetime.now(timezone.utc) < product.sale_start_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": 40905, "message": "开票时间未到"},
                )

            # 4. 计算价格并锁定库存（按日期逐天处理）
            for d in dates:
                # 锁定库存
                await inventory_service.lock_inventory(
                    db, product_id, d, quantity, order_id=0,
                    sku_id=sku_id, time_slot=time_slot,
                )
                locked_inventories.append((product_id, d, quantity, sku_id, time_slot))

                # 计算价格：4级优先级链定价
                day_price = await _resolve_price(db, product, d)
                actual_price = day_price * quantity

                # 创建订单项
                order_items.append({
                    "product_id": product_id,
                    "sku_id": sku_id,
                    "date": d,
                    "time_slot": time_slot,
                    "quantity": quantity,
                    "unit_price": day_price,
                    "actual_price": actual_price,
                    "identity_ids": identity_ids,
                    "parent_item_id": item_data.get("parent_order_item_id"),
                })
                total_amount += actual_price

            # 押金（租赁类）
            if product.ext_rental and product.ext_rental.deposit_amount > 0:
                deposit_amount += product.ext_rental.deposit_amount * quantity

        # 5. 应用折扣规则（连续天数折扣 vs 多人折扣，互斥取最优）
        discount_amount, discount_type_result, discount_detail_result = (
            await _calculate_discount(db, items_data, order_items, total_amount)
        )

        # 6. 创建订单
        actual_amount = total_amount - discount_amount + deposit_amount
        payment_timeout = 1800  # 默认30分钟

        order = Order(
            order_no=generate_order_no(),
            user_id=user.id,
            order_type=order_type,
            status="pending_payment",
            total_amount=total_amount,
            discount_amount=discount_amount,
            actual_amount=actual_amount,
            deposit_amount=deposit_amount,
            discount_type=discount_type_result,
            discount_detail=discount_detail_result,
            payment_method=payment_method,
            payment_status="unpaid",
            times_card_id=times_card_id,
            address_id=address_id,
            remark=remark,
            expire_at=datetime.now(timezone.utc) + timedelta(seconds=payment_timeout),
        )
        db.add(order)
        await db.flush()

        # 7. 创建订单项
        for oi_data in order_items:
            identity_ids = oi_data.pop("identity_ids", [])
            parent_item_id = oi_data.pop("parent_item_id", None)

            # 如果有多个身份信息，为每个身份创建一个订单项
            if identity_ids:
                for identity_id in identity_ids:
                    oi = OrderItem(
                        order_id=order.id,
                        identity_id=identity_id,
                        parent_item_id=parent_item_id,
                        **oi_data,
                    )
                    db.add(oi)
            else:
                oi = OrderItem(
                    order_id=order.id,
                    parent_item_id=parent_item_id,
                    **oi_data,
                )
                db.add(oi)

        await db.flush()
        logger.info(f"[订单] 创建: order_id={order.id}, order_no={order.order_no}, user={user.id}")

        return order

    except Exception:
        # 回滚已锁定的库存（任何异常都必须释放，防止库存死锁）
        for pid, d, qty, sid, ts in locked_inventories:
            try:
                await inventory_service.release_inventory(db, pid, d, qty, 0, sid, ts)
            except Exception:
                logger.error(f"[订单] 回滚库存失败: product={pid}, date={d}")
        raise


async def cancel_order(
    db: AsyncSession,
    order_id: int,
    user_id: int,
    reason: Optional[str] = None,
) -> Order:
    """取消订单（仅限待支付状态）

    Args:
        db: 数据库会话
        order_id: 订单ID
        user_id: 当前用户ID
        reason: 取消原因

    Returns:
        取消后的 Order
    """
    order = await _get_user_order(db, order_id, user_id)

    if order.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "订单状态不允许取消"},
        )

    order.status = "cancelled"
    order.remark = reason or order.remark

    # 释放库存
    for item in order.items:
        if item.date:
            await inventory_service.release_inventory(
                db, item.product_id, item.date, item.quantity,
                order.id, item.sku_id, item.time_slot,
            )

    await db.flush()
    logger.info(f"[订单] 取消: order_id={order_id}, user={user_id}")
    return order


async def apply_refund(
    db: AsyncSession,
    order_id: int,
    user_id: int,
    reason: Optional[str] = None,
    order_item_ids: Optional[List[int]] = None,
) -> Order:
    """申请退票

    Args:
        db: 数据库会话
        order_id: 订单ID
        user_id: 用户ID
        reason: 退票原因
        order_item_ids: 指定退票的订单项（为空则全额退）

    Returns:
        更新后的 Order
    """
    order = await _get_user_order(db, order_id, user_id)

    if order.status not in ("paid", "verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "订单状态不允许退票"},
        )

    # 校验退票截止时间
    if order.status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40903, "message": "已验票，如需退款请联系客服"},
        )

    first_item = order.items[0] if order.items else None
    if first_item and first_item.product_id:
        product_result = await db.execute(
            select(Product).where(Product.id == first_item.product_id)
        )
        product = product_result.scalar_one_or_none()
        if product:
            now = datetime.now(timezone.utc)
            item_date = first_item.date
            if item_date:
                # 将 date 转为 datetime（当天 00:00 UTC）
                item_datetime = datetime(
                    item_date.year, item_date.month, item_date.day,
                    tzinfo=timezone.utc,
                )
                if product.refund_deadline_type == "days":
                    deadline = item_datetime - timedelta(days=product.refund_deadline_value)
                else:  # hours
                    deadline = item_datetime - timedelta(hours=product.refund_deadline_value)

                if now >= deadline:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": 40903, "message": "已超过退票时间，无法退票"},
                    )

    # 退票金额计算
    refund_amount = Decimal("0")
    if order_item_ids:
        # 部分退票：仅退指定的 OrderItem
        refund_items = [item for item in order.items if item.id in order_item_ids]
        if not refund_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40001, "message": "指定的订单项不存在"},
            )

        for item in refund_items:
            refund_amount += item.actual_price
            item.refund_status = "refunded"
            # 释放对应日期库存
            if item.date:
                await _refund_inventory(
                    db, item.product_id, item.date, item.quantity,
                    order.id, item.sku_id, item.time_slot,
                )

        # 判断是否全部退完
        all_refunded = all(item.refund_status == "refunded" for item in order.items)
        if all_refunded:
            order.status = "refunded"
            order.payment_status = "refunded"
        else:
            order.status = "partial_refunded"
            order.payment_status = "partial_refunded"

        logger.info(
            f"[订单] 部分退票: order_id={order_id}, items={order_item_ids}, "
            f"refund_amount={refund_amount}"
        )
        order.remark = reason or order.remark
        await db.flush()
        return order
    else:
        # 全额退票
        refund_amount = order.actual_amount

    order.status = "refund_pending"
    order.remark = reason or order.remark

    await db.flush()
    logger.info(f"[订单] 申请退票: order_id={order_id}, user={user_id}")
    return order


async def approve_refund(
    db: AsyncSession,
    order_id: int,
    approved: bool,
    reject_reason: Optional[str] = None,
    operator_id: int = 0,
) -> Order:
    """审批退款（管理端）

    Args:
        db: 数据库会话
        order_id: 订单ID
        approved: 是否通过
        reject_reason: 拒绝原因
        operator_id: 操作人ID

    Returns:
        更新后的 Order
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.is_deleted.is_(False))
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )

    if order.status != "refund_pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "订单不在退款审批状态"},
        )

    if approved:
        order.status = "refunded"
        order.payment_status = "refunded"

        # 释放库存
        for item in order.items:
            item.refund_status = "refunded"
            if item.date:
                # 退款：已售 → 可用
                await _refund_inventory(
                    db, item.product_id, item.date, item.quantity,
                    order.id, item.sku_id, item.time_slot,
                )

        # TODO: 调用微信退款接口
    else:
        order.status = "paid"  # 驳回，恢复已支付状态
        order.remark = f"退款被拒绝: {reject_reason}" if reject_reason else order.remark

    await db.flush()
    logger.info(
        f"[订单] 退款审批: order_id={order_id}, approved={approved}, operator={operator_id}"
    )
    return order


async def mock_pay_order(
    db: AsyncSession,
    order_id: int,
    user_id: int,
    success: bool = True,
) -> Order:
    """模拟支付

    Args:
        db: 数据库会话
        order_id: 订单ID
        user_id: 用户ID
        success: 模拟成功/失败

    Returns:
        支付后的 Order
    """
    order = await _get_user_order(db, order_id, user_id)

    if order.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "订单状态不允许支付"},
        )

    # 检查是否超时
    if order.expire_at and datetime.now(timezone.utc) > order.expire_at:
        order.status = "cancelled"
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40904, "message": "支付超时，订单已取消"},
        )

    if success:
        order.status = "paid"
        order.payment_status = "paid"
        order.payment_time = datetime.now(timezone.utc)
        order.payment_no = f"MOCK_{order.order_no}"

        # 确认售出（锁定→已售）
        for item in order.items:
            if item.date:
                await inventory_service.confirm_sell(
                    db, item.product_id, item.date, item.quantity,
                    order.id, item.sku_id, item.time_slot,
                )

        # 生成电子票
        await _generate_tickets(db, order)
    else:
        order.status = "cancelled"
        order.remark = "模拟支付失败"
        # 释放库存
        for item in order.items:
            if item.date:
                await inventory_service.release_inventory(
                    db, item.product_id, item.date, item.quantity,
                    order.id, item.sku_id, item.time_slot,
                )

    await db.flush()
    logger.info(
        f"[订单] 模拟支付: order_id={order_id}, success={success}, user={user_id}"
    )
    return order


async def initiate_payment(
    db: AsyncSession,
    order_id: int,
    user_id: int,
    payment_method: str = "wechat_pay",
) -> Dict[str, Any]:
    """发起支付

    Args:
        db: 数据库会话
        order_id: 订单ID
        user_id: 用户ID
        payment_method: 支付方式

    Returns:
        微信支付调起参数 或 模拟支付结果
    """
    order = await _get_user_order(db, order_id, user_id)

    if order.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "订单状态不允许支付"},
        )

    if order.expire_at and datetime.now(timezone.utc) > order.expire_at:
        order.status = "cancelled"
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40904, "message": "支付超时"},
        )

    # TODO: 调用微信支付统一下单接口
    return {
        "appId": "",
        "timeStamp": str(int(datetime.now(timezone.utc).timestamp())),
        "nonceStr": generate_qr_token()[:16],
        "package": f"prepay_id=mock_{order.order_no}",
        "signType": "RSA",
        "paySign": "mock_sign",
    }


async def seckill_order(
    db: AsyncSession,
    user: User,
    product_id: int,
    booking_date: date,
    quantity: int = 1,
    sku_id: Optional[int] = None,
    identity_ids: Optional[List[int]] = None,
    disclaimer_signed: bool = False,
) -> Order:
    """秒杀下单

    使用 Redis 预扣库存，简化流程

    Args:
        db: 数据库会话
        user: 用户
        product_id: 商品ID
        booking_date: 预约日期
        quantity: 数量
        sku_id: SKU ID
        identity_ids: 身份信息ID
        disclaimer_signed: 是否已签免责

    Returns:
        创建的 Order
    """
    redis = get_redis()

    # Redis 预扣库存
    stock_key = f"seckill_stock:{product_id}:{booking_date}"
    user_key = f"seckill_user:{product_id}:{booking_date}:{user.id}"

    # 检查是否已抢购
    if await redis.exists(user_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40919, "message": "重复预定（同天同商品）"},
        )

    # 预扣库存
    remaining = await redis.decrby(stock_key, quantity)
    if remaining < 0:
        await redis.incrby(stock_key, quantity)  # 回滚
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": "库存不足，秒杀失败"},
        )

    # 标记已抢购（防重复，过期时间30分钟）
    await redis.set(user_key, "1", ex=1800)

    # 创建订单（复用普通下单流程）
    items_data = [{
        "product_id": product_id,
        "sku_id": sku_id,
        "quantity": quantity,
        "dates": [booking_date],
        "identity_ids": identity_ids or [],
    }]

    try:
        order = await create_order(
            db, user, items_data,
            disclaimer_signed=disclaimer_signed,
            payment_method="wechat_pay",
        )
        return order
    except Exception:
        # 回滚 Redis 库存
        await redis.incrby(stock_key, quantity)
        await redis.delete(user_key)
        raise


async def get_order_detail(
    db: AsyncSession,
    order_id: int,
    user_id: Optional[int] = None,
) -> Order:
    """获取订单详情

    Args:
        db: 数据库会话
        order_id: 订单ID
        user_id: 用户ID（为None则不校验归属）

    Returns:
        Order 实例
    """
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.is_deleted.is_(False))
    )
    if user_id:
        query = query.where(Order.user_id == user_id)

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )

    return order


async def list_orders(
    db: AsyncSession,
    *,
    site_id: Optional[int] = None,
    user_id: Optional[int] = None,
    order_status: Optional[str] = None,
    order_type: Optional[str] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    keyword: Optional[str] = None,
    payment_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Tuple[List[Order], int]:
    """订单列表

    Args:
        db: 数据库会话
        site_id: 营地ID（SQL WHERE 过滤）
        user_id: 用户ID（C端）
        order_status: 订单状态
        order_type: 订单类型
        date_start: 下单日期开始
        date_end: 下单日期结束
        keyword: 搜索关键词
        payment_status: 支付状态
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        (订单列表, 总数)
    """
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.is_deleted.is_(False))
    )

    if site_id is not None:
        query = query.where(Order.site_id == site_id)
    if user_id:
        query = query.where(Order.user_id == user_id)
    if order_status:
        query = query.where(Order.status == order_status)
    if order_type:
        query = query.where(Order.order_type == order_type)
    if date_start:
        query = query.where(func.date(Order.created_at) >= date_start)
    if date_end:
        query = query.where(func.date(Order.created_at) <= date_end)
    if keyword:
        query = query.where(
            or_(
                Order.order_no.ilike(f"%{keyword}%"),
            )
        )
    if payment_status:
        query = query.where(Order.payment_status == payment_status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(Order, sort_by)
        query = query.order_by(order_col.desc() if sort_order == "desc" else order_col.asc())
    else:
        query = query.order_by(Order.id.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    orders = list(result.scalars().unique().all())

    return orders, total


async def update_shipping(
    db: AsyncSession,
    order_id: int,
    shipping_no: str,
    shipping_company: Optional[str] = None,
    operator_id: int = 0,
) -> Order:
    """更新物流信息

    Args:
        db: 数据库会话
        order_id: 订单ID
        shipping_no: 物流单号
        shipping_company: 物流公司
        operator_id: 操作人

    Returns:
        更新后的 Order
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.is_deleted.is_(False))
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )

    order.shipping_no = shipping_no
    order.shipping_status = "shipped"

    await db.flush()
    logger.info(f"[订单] 更新物流: order_id={order_id}, shipping_no={shipping_no}")
    return order


# ---- 内部方法 ----

async def _get_user_order(db: AsyncSession, order_id: int, user_id: int) -> Order:
    """获取用户的订单（带权限校验）"""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.id == order_id,
            Order.user_id == user_id,
            Order.is_deleted.is_(False),
        )
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )

    return order


async def _generate_tickets(db: AsyncSession, order: Order) -> List[Ticket]:
    """支付成功后生成电子票"""
    tickets = []
    ticket_type_map = {
        "daily_camping": "camping",
        "event_camping": "camping",
        "rental": "rental",
        "daily_activity": "activity",
        "special_activity": "activity",
    }
    ticket_type = ticket_type_map.get(order.order_type)
    if not ticket_type:
        return tickets

    for item in order.items:
        ticket = Ticket(
            order_id=order.id,
            order_item_id=item.id,
            user_id=order.user_id,
            ticket_no=generate_ticket_code(),
            ticket_type=ticket_type,
            qr_token=generate_qr_token(),
            qr_token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
            verify_date=item.date,
            verify_status="pending",
            total_verify_count=1,
            current_verify_count=0,
        )
        db.add(ticket)
        tickets.append(ticket)

    await db.flush()
    return tickets


async def _refund_inventory(
    db: AsyncSession,
    product_id: int,
    inv_date: date,
    quantity: int,
    order_id: int,
    sku_id: Optional[int] = None,
    time_slot: Optional[str] = None,
) -> None:
    """退款恢复库存（已售 → 可用）"""
    from models.product import InventoryLog

    query = select(Inventory).where(
        Inventory.product_id == product_id,
        Inventory.date == inv_date,
        Inventory.is_deleted.is_(False),
    )
    if sku_id:
        query = query.where(Inventory.sku_id == sku_id)
    if time_slot:
        query = query.where(Inventory.time_slot == time_slot)

    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if inv:
        refund_qty = min(quantity, inv.sold)
        inv.sold -= refund_qty
        inv.available += refund_qty

        log = InventoryLog(
            inventory_id=inv.id,
            change_type="refund",
            quantity=refund_qty,
            order_id=order_id,
            remark=f"退款恢复 order_id={order_id}",
        )
        db.add(log)


async def _resolve_price(
    db: AsyncSession,
    product: Product,
    target_date: date,
) -> Decimal:
    """4级优先级链动态定价

    1. 特定日期特殊价（最高优先级）
    2. 自定义日期类型价（DateTypeConfig 配置的日期类型）
    3. 系统日期类型价（自动判断 weekday/weekend）
    4. 商品基础价（兜底）

    Args:
        db: 数据库会话
        product: 商品实例
        target_date: 目标日期

    Returns:
        当天适用价格
    """
    # 1. 特定日期特殊价
    rule_result = await db.execute(
        select(PricingRule).where(
            PricingRule.product_id == product.id,
            PricingRule.rule_type == "custom_date",
            PricingRule.custom_date == target_date,
        )
    )
    custom_rule = rule_result.scalar_one_or_none()
    if custom_rule:
        logger.info(
            f"[定价] 命中特定日期价: product={product.id}, date={target_date}, "
            f"price={custom_rule.price}"
        )
        return custom_rule.price

    # 2. 自定义日期类型价（查 DateTypeConfig）
    dtc_result = await db.execute(
        select(DateTypeConfig).where(
            DateTypeConfig.date == target_date,
            DateTypeConfig.site_id == product.site_id,
        )
    )
    date_type_config = dtc_result.scalar_one_or_none()

    if date_type_config:
        dtype_rule_result = await db.execute(
            select(PricingRule).where(
                PricingRule.product_id == product.id,
                PricingRule.rule_type == "date_type",
                PricingRule.date_type == date_type_config.date_type,
            )
        )
        dtype_rule = dtype_rule_result.scalar_one_or_none()
        if dtype_rule:
            logger.info(
                f"[定价] 命中自定义日期类型价: product={product.id}, "
                f"date={target_date}, type={date_type_config.date_type}, "
                f"price={dtype_rule.price}"
            )
            return dtype_rule.price

    # 3. 系统日期类型价（周一~周五=weekday, 周六日=weekend）
    system_date_type = "weekend" if target_date.weekday() >= 5 else "weekday"
    sys_rule_result = await db.execute(
        select(PricingRule).where(
            PricingRule.product_id == product.id,
            PricingRule.rule_type == "date_type",
            PricingRule.date_type == system_date_type,
        )
    )
    sys_rule = sys_rule_result.scalar_one_or_none()
    if sys_rule:
        logger.info(
            f"[定价] 命中系统日期类型价: product={product.id}, "
            f"date={target_date}, type={system_date_type}, price={sys_rule.price}"
        )
        return sys_rule.price

    # 4. 商品基础价（兜底）
    logger.info(
        f"[定价] 使用基础价: product={product.id}, date={target_date}, "
        f"price={product.base_price}"
    )
    return product.base_price


async def _calculate_discount(
    db: AsyncSession,
    items_data: List[Dict[str, Any]],
    order_items: List[Dict[str, Any]],
    total_amount: Decimal,
) -> Tuple[Decimal, Optional[str], Optional[Dict]]:
    """计算折扣（连续天数 vs 多人，互斥取最优）

    Args:
        db: 数据库会话
        items_data: 原始下单数据
        order_items: 已计算价格的订单项
        total_amount: 原总价

    Returns:
        (discount_amount, discount_type, discount_detail)
    """
    if not order_items:
        return Decimal("0"), None, None

    # 收集商品 ID 列表
    product_ids = list({oi["product_id"] for oi in order_items})

    # 查询适用的折扣规则（商品级 + 全局）
    discount_rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.status == "active",
            or_(
                DiscountRule.product_id.in_(product_ids),
                DiscountRule.product_id.is_(None),
            ),
        )
    )
    discount_rules = list(discount_rules_result.scalars().all())

    if not discount_rules:
        return Decimal("0"), None, None

    # 计算连续天数
    all_dates = sorted({oi["date"] for oi in order_items if oi.get("date")})
    consecutive_days = _count_consecutive_days(all_dates)

    # 计算总人数（quantity 之和）
    total_quantity = sum(oi["quantity"] for oi in order_items)

    best_discount_amount = Decimal("0")
    best_discount_type: Optional[str] = None
    best_discount_detail: Optional[Dict] = None

    for rule in discount_rules:
        if rule.rule_type == "consecutive_days" and consecutive_days >= rule.threshold:
            discounted_total = total_amount * rule.discount_rate
            discount_amt = total_amount - discounted_total
            if discount_amt > best_discount_amount:
                best_discount_amount = discount_amt
                best_discount_type = "consecutive_days"
                best_discount_detail = {
                    "rule_id": rule.id,
                    "rule_type": "consecutive_days",
                    "consecutive_days": consecutive_days,
                    "threshold": rule.threshold,
                    "discount_rate": str(rule.discount_rate),
                    "discount_amount": str(discount_amt),
                }

        elif rule.rule_type == "multi_person" and total_quantity >= rule.threshold:
            discounted_total = total_amount * rule.discount_rate
            discount_amt = total_amount - discounted_total
            if discount_amt > best_discount_amount:
                best_discount_amount = discount_amt
                best_discount_type = "multi_person"
                best_discount_detail = {
                    "rule_id": rule.id,
                    "rule_type": "multi_person",
                    "total_quantity": total_quantity,
                    "threshold": rule.threshold,
                    "discount_rate": str(rule.discount_rate),
                    "discount_amount": str(discount_amt),
                }

    if best_discount_amount > Decimal("0"):
        logger.info(
            f"[折扣] 应用: type={best_discount_type}, "
            f"discount_amount={best_discount_amount}"
        )

    return best_discount_amount, best_discount_type, best_discount_detail


def _count_consecutive_days(dates: List[date]) -> int:
    """计算连续天数"""
    if not dates:
        return 0
    max_consecutive = 1
    current = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current += 1
            max_consecutive = max(max_consecutive, current)
        else:
            current = 1
    return max_consecutive
