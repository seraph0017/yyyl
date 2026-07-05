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

import hashlib
import hmac
import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from models.order import Order, OrderItem, TemporaryOrderSession, Ticket
from models.product import DateTypeConfig, DiscountRule, Inventory, PricingRule, Product, SKU
from models.user import User, UserAddress, UserIdentity
from redis_client import get_redis
from services import inventory_pool_service, inventory_service, member_service, qrcode_service, settlement_service, ticket_service, wechat_pay_service
from utils.helpers import generate_order_no, generate_qr_token, generate_ticket_code

logger = logging.getLogger(__name__)

CAMPSITE_PRODUCT_TYPES = {"daily_camping", "event_camping"}
ACTIVITY_PRODUCT_TYPES = {"daily_activity", "special_activity"}
DATE_INVENTORY_PRODUCT_TYPES = CAMPSITE_PRODUCT_TYPES | ACTIVITY_PRODUCT_TYPES
TEMPORARY_ORDER_EXPIRE_SECONDS = 15 * 60

# 排序字段白名单
ALLOWED_SORT_FIELDS = {"id", "created_at", "actual_amount", "status"}


def _first_product_image(product: Optional[Product]) -> Optional[str]:
    """取商品图片列表中的首图，兼容历史 string 和 {url} 两种结构。"""
    if product is None:
        return None
    images = getattr(product, "images", None) or []
    if not isinstance(images, list) or not images:
        return None
    sorted_images = sorted(
        images,
        key=lambda image: image.get("sort_order", 0) if isinstance(image, dict) else 0,
    )
    first = sorted_images[0]
    if isinstance(first, dict):
        return first.get("url") or first.get("src")
    if isinstance(first, str):
        return first
    return None


async def _resolve_primary_identity_id(
    db: AsyncSession,
    user: User,
    identity_ids: Optional[List[int]],
) -> Optional[int]:
    """校验出行人身份归属，并返回当前订单项记录的主出行人 ID。"""
    normalized_ids = [int(identity_id) for identity_id in (identity_ids or []) if identity_id]
    if not normalized_ids:
        return None

    unique_ids = set(normalized_ids)
    result = await db.execute(
        select(UserIdentity.id).where(
            UserIdentity.id.in_(unique_ids),
            UserIdentity.user_id == user.id,
            UserIdentity.is_deleted.is_(False),
        )
    )
    valid_ids = set(result.scalars().all())
    if valid_ids != unique_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40021, "message": "出行人信息不存在或不属于当前用户"},
        )
    return normalized_ids[0]


async def _resolve_shipping_address(
    db: AsyncSession,
    user: User,
    address_id: Optional[int],
    *,
    shipping_required: bool,
) -> Optional[UserAddress]:
    """校验邮寄地址归属，需邮寄商品必须提供当前用户地址。"""
    if not shipping_required:
        return None
    if not address_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40917, "message": "邮寄商品请选择收货地址"},
        )

    result = await db.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user.id,
            UserAddress.is_deleted.is_(False),
        )
    )
    address = result.scalar_one_or_none()
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "收货地址不存在或不属于当前用户"},
        )
    return address


async def _attach_order_display_fields(db: AsyncSession, orders: List[Order]) -> None:
    """为订单响应补充前端展示字段，避免序列化阶段触发懒加载。"""
    order_items: List[OrderItem] = []
    order_user_by_item: Dict[int, int] = {}
    order_user_ids: set[int] = set()
    for order in orders:
        order_user_id = getattr(order, "user_id", None)
        if order_user_id:
            order_user_ids.add(order_user_id)
        for item in list(getattr(order, "items", []) or []):
            order_items.append(item)
            if order_user_id:
                order_user_by_item[id(item)] = order_user_id
    if not order_items:
        return

    product_ids = {item.product_id for item in order_items if item.product_id}
    sku_ids = {item.sku_id for item in order_items if item.sku_id}
    identity_ids = {item.identity_id for item in order_items if item.identity_id}

    products_by_id: Dict[int, Product] = {}
    if product_ids:
        product_result = await db.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.is_deleted.is_(False),
            )
        )
        products_by_id = {product.id: product for product in product_result.scalars().all()}

    skus_by_id: Dict[int, SKU] = {}
    if sku_ids:
        sku_result = await db.execute(
            select(SKU).where(
                SKU.id.in_(sku_ids),
                SKU.is_deleted.is_(False),
            )
        )
        skus_by_id = {sku.id: sku for sku in sku_result.scalars().all()}

    identities_by_id: Dict[int, UserIdentity] = {}
    if identity_ids and order_user_ids:
        identity_result = await db.execute(
            select(UserIdentity).where(
                UserIdentity.id.in_(identity_ids),
                UserIdentity.user_id.in_(order_user_ids),
                UserIdentity.is_deleted.is_(False),
            )
        )
        identities_by_id = {identity.id: identity for identity in identity_result.scalars().all()}

    for order in orders:
        order_remark = getattr(order, "remark", None)
        for item in getattr(order, "items", []) or []:
            product = products_by_id.get(item.product_id)
            sku = skus_by_id.get(item.sku_id) if item.sku_id else None
            identity = identities_by_id.get(item.identity_id) if item.identity_id else None
            if identity and getattr(identity, "user_id", None) != order_user_by_item.get(id(item)):
                identity = None
            product_image = getattr(sku, "image_url", None) or _first_product_image(product)

            setattr(item, "product_name", getattr(product, "name", None))
            setattr(item, "product_image", product_image)
            setattr(item, "cover_image", product_image)
            setattr(item, "sku_spec_values", getattr(sku, "spec_values", None) if sku else None)
            setattr(item, "identity_name", getattr(identity, "name", None) if identity else None)
            setattr(item, "remark", order_remark)


def build_order_list_query(
    *,
    site_id: Optional[int] = None,
    user_id: Optional[int] = None,
    order_status: Optional[str] = None,
    order_type: Optional[str] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    payment_time_start: Optional[datetime] = None,
    payment_time_end: Optional[datetime] = None,
    amount_min: Optional[Decimal | float | int] = None,
    amount_max: Optional[Decimal | float | int] = None,
    keyword: Optional[str] = None,
    payment_status: Optional[str] = None,
    product_id: Optional[int] = None,
    sku_id: Optional[int] = None,
    product_type: Optional[str] = None,
    booking_date_start: Optional[date] = None,
    booking_date_end: Optional[date] = None,
    time_slot: Optional[str] = None,
    verify_status: Optional[str] = None,
    source_channel: Optional[str] = None,
) -> Any:
    """构造订单列表基础查询，供列表和导出复用。"""
    query = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .join(Order.user)
        .join(Order.items, isouter=True)
        .join(Product, Product.id == OrderItem.product_id, isouter=True)
        .outerjoin(Ticket, Ticket.order_item_id == OrderItem.id)
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
    if payment_time_start:
        query = query.where(Order.payment_time >= payment_time_start)
    if payment_time_end:
        query = query.where(Order.payment_time <= payment_time_end)
    if amount_min is not None:
        query = query.where(Order.actual_amount >= Decimal(str(amount_min)))
    if amount_max is not None:
        query = query.where(Order.actual_amount <= Decimal(str(amount_max)))
    if payment_status:
        query = query.where(Order.payment_status == payment_status)
    if product_id:
        query = query.where(OrderItem.product_id == product_id)
    if sku_id:
        query = query.where(OrderItem.sku_id == sku_id)
    if product_type:
        query = query.where(Product.type == product_type)
    if booking_date_start:
        query = query.where(OrderItem.date >= booking_date_start)
    if booking_date_end:
        query = query.where(OrderItem.date <= booking_date_end)
    if time_slot:
        query = query.where(OrderItem.time_slot == time_slot)
    if verify_status:
        query = query.where(Ticket.verify_status == verify_status)
    if source_channel:
        query = query.where(Order.source_channel == source_channel)
    if keyword:
        query = query.where(
            or_(
                Order.order_no.ilike(f"%{keyword}%"),
                User.nickname.ilike(f"%{keyword}%"),
                User.phone.ilike(f"%{keyword}%"),
                Product.name.ilike(f"%{keyword}%"),
            )
        )
    return query


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
    source_qrcode_id: Optional[int] = None,
    source_channel: Optional[str] = None,
    source_scanned_at: Optional[datetime] = None,
    payment_timeout_seconds: int = 1800,
    biz_data: Optional[Dict[str, Any]] = None,
    order_type_override: Optional[str] = None,
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
        source_qrcode_id: 来源小程序码ID
        source_channel: 来源渠道
        source_scanned_at: 来源扫码时间
        payment_timeout_seconds: 支付超时时间（秒）
        biz_data: 业务扩展数据
        order_type_override: 强制订单类型

    Returns:
        创建的 Order 实例

    Raises:
        HTTPException: 各种业务校验失败
    """
    total_amount = Decimal("0")
    discount_amount = Decimal("0")
    deposit_amount = Decimal("0")
    order_type = ""
    order_site_id: Optional[int] = None
    user_site_id = getattr(user, "site_id", None)
    order_items: List[Dict[str, Any]] = []
    locked_inventories: List[Tuple[int, Any, int, Any, Any]] = []  # 记录已锁定的旧库存，异常时回滚
    locked_inventory_pools: List[Tuple[int, int]] = []  # 记录已锁定的共享库存池，异常时回滚
    locked_skus: List[Tuple[int, int]] = []  # 记录已预扣的无日期 SKU 静态库存
    shipping_required = False
    shipping_address: Optional[UserAddress] = None

    try:
        for item_data in items_data:
            product_id = item_data["product_id"]
            sku_id = item_data.get("sku_id")
            quantity = item_data.get("quantity", 1)
            dates = item_data.get("dates", [])
            time_slot = item_data.get("time_slot")
            identity_ids = item_data.get("identity_ids", [])
            primary_identity_id = await _resolve_primary_identity_id(db, user, identity_ids)

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
            if user_site_id is not None and product.site_id != user_site_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": 40401, "message": f"商品不存在或已下架: id={product_id}"},
                )
            if order_site_id is None:
                order_site_id = product.site_id
            elif order_site_id != product.site_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": 40002, "message": "同一订单不能包含不同营地商品"},
                )

            is_campsite_product = product.type in CAMPSITE_PRODUCT_TYPES
            is_activity_product = product.type in ACTIVITY_PRODUCT_TYPES
            is_date_inventory_product = product.type in DATE_INVENTORY_PRODUCT_TYPES
            if is_campsite_product and not dates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": 40916, "message": "营位商品请选择预约日期"},
                )
            if is_activity_product and not dates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": 40916, "message": "活动商品请选择预约日期"},
                )
            if is_activity_product and not time_slot:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": 40918, "message": "活动商品请选择预约时间"},
                )
            if not is_date_inventory_product:
                dates = []

            # 确定订单类型（取第一个商品类型）
            if not order_type:
                order_type = product.type

            if product.ext_shop and product.ext_shop.shipping_required:
                shipping_required = True

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
                inventory_pool_id = await _lock_inventory_for_order_item(
                    db,
                    site_id=product.site_id,
                    product_id=product_id,
                    sku_id=sku_id,
                    inv_date=d,
                    quantity=quantity,
                    order_id=0,
                    time_slot=time_slot,
                    locked_inventories=locked_inventories,
                    locked_inventory_pools=locked_inventory_pools,
                )

                # 计算价格：4级优先级链定价
                day_price = await _resolve_price(db, product, d, sku_id=sku_id)
                actual_price = day_price * quantity

                # 创建订单项
                order_items.append({
                    "product_id": product_id,
                    "sku_id": sku_id,
                    "inventory_pool_id": inventory_pool_id,
                    "date": d,
                    "time_slot": time_slot,
                    "quantity": quantity,
                    "unit_price": day_price,
                    "actual_price": actual_price,
                    "identity_id": primary_identity_id,
                    "parent_item_id": item_data.get("parent_order_item_id"),
                })
                total_amount += actual_price

            # 无日期库存商品不按日期拆单，直接按购买数量生成一个无日期订单项
            if not is_date_inventory_product:
                inventory_pool_id = await _lock_inventory_for_order_item(
                    db,
                    site_id=product.site_id,
                    product_id=product_id,
                    sku_id=sku_id,
                    inv_date=None,
                    quantity=quantity,
                    order_id=0,
                    time_slot=time_slot,
                    locked_inventories=locked_inventories,
                    locked_inventory_pools=locked_inventory_pools,
                )
                if inventory_pool_id is None and sku_id:
                    await _lock_static_sku_stock(db, product, sku_id, quantity, locked_skus)
                unit_price = await _resolve_sku_price(db, product, sku_id)
                actual_price = unit_price * quantity
                order_items.append({
                    "product_id": product_id,
                    "sku_id": sku_id,
                    "inventory_pool_id": inventory_pool_id,
                    "date": None,
                    "time_slot": time_slot,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "actual_price": actual_price,
                    "identity_id": primary_identity_id,
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

        shipping_address = await _resolve_shipping_address(
            db,
            user,
            address_id,
            shipping_required=shipping_required,
        )

        # 6. 创建订单
        actual_amount = total_amount - discount_amount + deposit_amount
        payment_timeout = payment_timeout_seconds

        order = Order(
            order_no=generate_order_no(),
            user_id=user.id,
            order_type=order_type_override or order_type,
            status="pending_payment",
            total_amount=total_amount,
            discount_amount=discount_amount,
            actual_amount=actual_amount,
            deposit_amount=deposit_amount,
            discount_type=discount_type_result,
            discount_detail=discount_detail_result,
            biz_data=biz_data,
            payment_method=payment_method,
            payment_status="unpaid",
            site_id=order_site_id or user_site_id or 1,
            times_card_id=times_card_id,
            address_id=shipping_address.id if shipping_address else address_id,
            remark=remark,
            expire_at=datetime.now(timezone.utc) + timedelta(seconds=payment_timeout),
            source_qrcode_id=source_qrcode_id,
            source_channel=source_channel,
            source_scanned_at=source_scanned_at,
        )
        db.add(order)
        await db.flush()

        # 7. 创建订单项
        for oi_data in order_items:
            identity_id = oi_data.pop("identity_id", None)
            parent_item_id = oi_data.pop("parent_item_id", None)

            oi = OrderItem(
                order_id=order.id,
                identity_id=identity_id,
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
        for pool_id, qty in locked_inventory_pools:
            try:
                await inventory_pool_service.release_pool_inventory(db, pool_id=pool_id, quantity=qty)
            except Exception:
                logger.error(f"[订单] 回滚共享库存池失败: pool={pool_id}")
        for sid, qty in locked_skus:
            try:
                await _release_static_sku_stock(db, sid, qty)
            except Exception:
                logger.error(f"[订单] 回滚 SKU 静态库存失败: sku={sid}")
        raise


async def quote_order(
    db: AsyncSession,
    user: User,
    items_data: List[Dict[str, Any]],
    *,
    disclaimer_signed: bool = False,
) -> Dict[str, Any]:
    """订单确认页报价与库存预校验，不锁库存、不创建订单。"""
    total_amount = Decimal("0")
    deposit_amount = Decimal("0")
    order_type = ""
    order_site_id: Optional[int] = None
    user_site_id = getattr(user, "site_id", None)
    quote_items: List[Dict[str, Any]] = []
    discount_items: List[Dict[str, Any]] = []
    pool_requirements: Dict[int, int] = {}
    inventory_requirements: Dict[Tuple[int, int, Any, str], int] = {}
    sku_requirements: Dict[int, int] = {}

    for item_data in items_data:
        product_id = item_data["product_id"]
        sku_id = item_data.get("sku_id")
        quantity = item_data.get("quantity", 1)
        dates = item_data.get("dates", [])
        time_slot = item_data.get("time_slot")

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
        if user_site_id is not None and product.site_id != user_site_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 40401, "message": f"商品不存在或已下架: id={product_id}"},
            )
        if order_site_id is None:
            order_site_id = product.site_id
        elif order_site_id != product.site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40002, "message": "同一订单不能包含不同营地商品"},
            )

        is_campsite_product = product.type in CAMPSITE_PRODUCT_TYPES
        is_activity_product = product.type in ACTIVITY_PRODUCT_TYPES
        is_date_inventory_product = product.type in DATE_INVENTORY_PRODUCT_TYPES
        if is_campsite_product and not dates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40916, "message": "营位商品请选择预约日期"},
            )
        if is_activity_product and not dates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40916, "message": "活动商品请选择预约日期"},
            )
        if is_activity_product and not time_slot:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40918, "message": "活动商品请选择预约时间"},
            )
        if not is_date_inventory_product:
            dates = []

        if not order_type:
            order_type = product.type

        if product.require_disclaimer and not disclaimer_signed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40915, "message": "请先签署免责声明"},
            )
        if product.sale_start_at and datetime.now(timezone.utc) < product.sale_start_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40905, "message": "开票时间未到"},
            )

        for d in dates:
            inventory_source, inventory_pool_id, available = await _quote_inventory_for_order_item(
                db,
                site_id=product.site_id,
                product_id=product_id,
                sku_id=sku_id,
                inv_date=d,
                quantity=quantity,
                time_slot=time_slot,
                pool_requirements=pool_requirements,
                inventory_requirements=inventory_requirements,
            )
            day_price = await _resolve_price(db, product, d, sku_id=sku_id)
            actual_price = day_price * quantity
            quote_item = {
                "product_id": product_id,
                "sku_id": sku_id,
                "product_name": product.name,
                "date": d,
                "time_slot": time_slot,
                "quantity": quantity,
                "unit_price": day_price,
                "actual_price": actual_price,
                "inventory_source": inventory_source,
                "inventory_pool_id": inventory_pool_id,
                "available": available,
            }
            quote_items.append(quote_item)
            discount_items.append({
                "product_id": product_id,
                "sku_id": sku_id,
                "date": d,
                "time_slot": time_slot,
                "quantity": quantity,
                "unit_price": day_price,
                "actual_price": actual_price,
            })
            total_amount += actual_price

        if not is_date_inventory_product:
            inventory_source, inventory_pool_id, available = await _quote_inventory_for_order_item(
                db,
                site_id=product.site_id,
                product_id=product_id,
                sku_id=sku_id,
                inv_date=None,
                quantity=quantity,
                time_slot=time_slot,
                pool_requirements=pool_requirements,
                inventory_requirements=inventory_requirements,
            )
            if inventory_source == "none" and sku_id:
                available = await _quote_static_sku_stock(
                    db,
                    product,
                    sku_id,
                    quantity,
                    sku_requirements,
                )
            unit_price = await _resolve_sku_price(db, product, sku_id)
            actual_price = unit_price * quantity
            quote_item = {
                "product_id": product_id,
                "sku_id": sku_id,
                "product_name": product.name,
                "date": None,
                "time_slot": time_slot,
                "quantity": quantity,
                "unit_price": unit_price,
                "actual_price": actual_price,
                "inventory_source": inventory_source,
                "inventory_pool_id": inventory_pool_id,
                "available": available,
            }
            quote_items.append(quote_item)
            discount_items.append({
                "product_id": product_id,
                "sku_id": sku_id,
                "date": None,
                "time_slot": time_slot,
                "quantity": quantity,
                "unit_price": unit_price,
                "actual_price": actual_price,
            })
            total_amount += actual_price

        if product.ext_rental and product.ext_rental.deposit_amount > 0:
            deposit_amount += product.ext_rental.deposit_amount * quantity

    discount_amount, discount_type, discount_detail = await _calculate_discount(
        db, items_data, discount_items, total_amount
    )
    actual_amount = total_amount - discount_amount + deposit_amount
    return {
        "items": quote_items,
        "total_amount": total_amount,
        "discount_amount": discount_amount,
        "actual_amount": actual_amount,
        "deposit_amount": deposit_amount,
        "discount_type": discount_type,
        "discount_detail": discount_detail,
        "has_shared_inventory": any(item.get("inventory_pool_id") for item in quote_items),
        "order_type": order_type,
        "site_id": order_site_id or user_site_id or 1,
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_temporary_order_token() -> str:
    return secrets.token_urlsafe(24)


def _generate_temporary_session_no() -> str:
    return generate_order_no("TO")


def hash_temporary_order_token(token: str) -> str:
    secret = settings.JWT_SECRET_KEY.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def _mask_auth_code(auth_code: str) -> str:
    if len(auth_code) <= 10:
        return f"{auth_code[:2]}******{auth_code[-2:]}"
    return f"{auth_code[:6]}******{auth_code[-4:]}"


def _temporary_biz_data(session: TemporaryOrderSession, *, custom_amount: bool) -> Dict[str, Any]:
    return {
        "temporary_order": {
            "session_id": session.id,
            "session_no": session.session_no,
            "payment_flow": session.payment_flow,
            "mode": session.mode,
            "custom_amount": custom_amount,
            "item_name": session.item_name,
            "amount": str(session.amount) if session.amount is not None else None,
            "remark": session.remark,
            "created_by_id": session.created_by_id,
            "created_by_source": session.created_by_source,
        }
    }


def _temporary_payment_timeout_seconds(session: TemporaryOrderSession) -> int:
    remaining = int((session.expire_at - _now()).total_seconds())
    return max(1, min(TEMPORARY_ORDER_EXPIRE_SECONDS, remaining))


def build_temporary_order_miniapp_path(token: str) -> str:
    return f"/pages/order-confirm/index?temporary_token={token}"


def build_temporary_session_response_payload(
    session: TemporaryOrderSession,
    *,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    audit_data = session.audit_data if isinstance(session.audit_data, dict) else {}
    payload = {
        "id": session.id,
        "session_no": session.session_no,
        "token": token,
        "status": session.status,
        "payment_flow": session.payment_flow,
        "mode": session.mode,
        "product_id": session.product_id,
        "sku_id": session.sku_id,
        "quantity": session.quantity,
        "booking_date": session.booking_date,
        "time_slot": session.time_slot,
        "item_name": session.item_name,
        "amount": session.amount,
        "remark": session.remark,
        "order_id": session.order_id,
        "expire_at": session.expire_at,
        "miniapp_path": build_temporary_order_miniapp_path(token) if token else None,
        "qrcode_image_url": audit_data.get("qrcode_image_url"),
    }
    return payload


async def create_temporary_order_session(
    db: AsyncSession,
    *,
    site_id: int,
    body: Any,
    operator_id: int,
    operator_source: str,
) -> Tuple[TemporaryOrderSession, str]:
    """创建现场临时订单/收款会话。"""
    if body.mode == "product":
        result = await db.execute(
            select(Product).where(
                Product.id == body.product_id,
                Product.site_id == site_id,
                Product.is_deleted.is_(False),
                Product.status == "on_sale",
            )
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 40401, "message": "商品不存在或已下架"},
            )
        if body.sku_id:
            sku_result = await db.execute(
                select(SKU).where(
                    SKU.id == body.sku_id,
                    SKU.product_id == body.product_id,
                    SKU.is_deleted.is_(False),
                    SKU.status == "active",
                )
            )
            if sku_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": 40405, "message": "SKU 不存在或已下架"},
                )
        if product.type in CAMPSITE_PRODUCT_TYPES and not body.booking_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40916, "message": "营位商品现场下单必须选择预约日期"},
            )

    now = _now()
    token = _generate_temporary_order_token()
    qrcode_image_url = None
    if body.payment_flow == "customer_scan_qr":
        qrcode_image_url = await qrcode_service.create_temporary_order_qrcode_image(
            site_id=site_id,
            token=token,
        )
    session = TemporaryOrderSession(
        site_id=site_id,
        session_no=_generate_temporary_session_no(),
        token_hash=hash_temporary_order_token(token),
        status="draft",
        payment_flow=body.payment_flow,
        mode=body.mode,
        product_id=body.product_id,
        sku_id=body.sku_id,
        quantity=body.quantity,
        booking_date=body.booking_date,
        time_slot=body.time_slot,
        item_name=(body.item_name.strip() if body.item_name else None),
        amount=body.amount,
        remark=(body.remark.strip() if body.remark else None),
        created_by_id=operator_id,
        created_by_source=operator_source,
        expire_at=now + timedelta(seconds=TEMPORARY_ORDER_EXPIRE_SECONDS),
        audit_data={
            "created_by_id": operator_id,
            "created_by_source": operator_source,
            "payment_flow": body.payment_flow,
            "mode": body.mode,
            "qrcode_image_url": qrcode_image_url,
        },
    )
    db.add(session)
    await db.flush()
    return session, token


async def _get_temporary_session_by_token(
    db: AsyncSession,
    *,
    site_id: int,
    token: str,
) -> TemporaryOrderSession:
    result = await db.execute(
        select(TemporaryOrderSession)
        .where(
            TemporaryOrderSession.site_id == site_id,
            TemporaryOrderSession.token_hash == hash_temporary_order_token(token),
            TemporaryOrderSession.is_deleted.is_(False),
        )
        .with_for_update()
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40441, "message": "临时收款会话不存在"},
        )
    return session


def _ensure_temporary_session_claimable(session: TemporaryOrderSession, *, site_id: int) -> None:
    if session.site_id != site_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40441, "message": "临时收款会话不存在"},
        )
    if session.status not in {"draft", "pending_payment"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40941, "message": "临时收款会话状态不允许继续支付"},
        )
    if session.expire_at <= _now():
        session.status = "expired"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40904, "message": "临时收款会话已过期"},
        )


async def _create_custom_temporary_order(
    db: AsyncSession,
    *,
    session: TemporaryOrderSession,
    user: User,
) -> Order:
    amount = Decimal(str(session.amount or "0")).quantize(Decimal("0.01"))
    order = Order(
        order_no=generate_order_no(),
        user_id=user.id,
        order_type="temporary",
        status="pending_payment",
        total_amount=amount,
        discount_amount=Decimal("0"),
        actual_amount=amount,
        deposit_amount=Decimal("0"),
        discount_type="none",
        discount_detail=None,
        biz_data=_temporary_biz_data(session, custom_amount=True),
        payment_method="wechat_pay",
        payment_status="unpaid",
        site_id=session.site_id,
        remark=session.remark,
        expire_at=session.expire_at,
        source_channel="onsite_temporary",
    )
    if isinstance(user, User):
        order.user = user
    db.add(order)
    await db.flush()
    return order


async def _create_product_temporary_order(
    db: AsyncSession,
    *,
    session: TemporaryOrderSession,
    user: User,
) -> Order:
    items_data = [{
        "product_id": session.product_id,
        "sku_id": session.sku_id,
        "quantity": session.quantity,
        "dates": [session.booking_date] if session.booking_date else [],
        "time_slot": session.time_slot,
        "identity_ids": [],
    }]
    order = await create_order(
        db,
        user,
        items_data,
        disclaimer_signed=True,
        remark=session.remark,
        payment_method="wechat_pay",
        source_channel="onsite_temporary",
        payment_timeout_seconds=_temporary_payment_timeout_seconds(session),
        biz_data=_temporary_biz_data(session, custom_amount=False),
    )
    order.expire_at = session.expire_at
    if isinstance(user, User):
        order.user = user
    await db.flush()
    return order


async def _create_order_from_temporary_session(
    db: AsyncSession,
    *,
    session: TemporaryOrderSession,
    user: User,
) -> Order:
    if session.order_id:
        return await get_order_detail(db, session.order_id, user_id=user.id)
    if session.mode == "custom_amount":
        return await _create_custom_temporary_order(db, session=session, user=user)
    return await _create_product_temporary_order(db, session=session, user=user)


async def claim_temporary_order_session(
    db: AsyncSession,
    *,
    site_id: int,
    token: str,
    user: User,
) -> Order:
    """顾客扫码后认领临时会话，并转正式订单。"""
    session = await _get_temporary_session_by_token(db, site_id=site_id, token=token)
    _ensure_temporary_session_claimable(session, site_id=site_id)
    if getattr(user, "site_id", site_id) != site_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40441, "message": "临时收款会话不存在"},
        )
    order = await _create_order_from_temporary_session(db, session=session, user=user)
    if session.order_id and order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40942, "message": "临时收款会话已被其他用户认领"},
        )
    session.order_id = order.id
    session.status = "pending_payment"
    audit_data = dict(session.audit_data or {})
    audit_data.update({
        "claimed_by_user_id": user.id,
        "claimed_at": _now().isoformat(),
        "order_id": order.id,
    })
    session.audit_data = audit_data
    await db.flush()
    return order


async def _get_or_create_onsite_guest_user(db: AsyncSession, *, site_id: int) -> User:
    openid = f"onsite:{site_id}"
    result = await db.execute(
        select(User).where(
            User.openid == openid,
            User.site_id == site_id,
            User.is_deleted.is_(False),
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        openid=openid,
        nickname="现场散客",
        role="user",
        site_id=site_id,
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


async def charge_temporary_order_by_auth_code(
    db: AsyncSession,
    *,
    site_id: int,
    session: TemporaryOrderSession,
    auth_code: str,
    device_id: Optional[str] = None,
) -> Tuple[Order, Dict[str, Any]]:
    """商户扫描用户付款码，走真实微信付款码接口。"""
    _ensure_temporary_session_claimable(session, site_id=site_id)
    user = await _get_or_create_onsite_guest_user(db, site_id=site_id)
    order = await _create_order_from_temporary_session(db, session=session, user=user)
    if getattr(order, "id", None):
        order = await get_order_detail(db, order.id, user_id=user.id)
    session.order_id = order.id
    audit_data = dict(session.audit_data or {})
    audit_data.update({
        "auth_code_masked": _mask_auth_code(auth_code),
        "device_id": device_id,
        "order_id": order.id,
    })
    session.audit_data = audit_data

    try:
        result = await wechat_pay_service.create_codepay_transaction(
            order,
            auth_code=auth_code,
            site_id=site_id,
            device_id=device_id,
        )
    except wechat_pay_service.WechatPayError as exc:
        order.remark = f"{order.remark or ''} 付款码收款待确认".strip()
        session.status = "pending_payment"
        audit_data = dict(session.audit_data or {})
        audit_data.update({"wechat_trade_state": "UNKNOWN", "requires_query": True})
        session.audit_data = audit_data
        await db.flush()
        logger.warning(
            "[现场收款] 微信付款码状态未知，保留本地订单等待查单: order_id=%s, error=%s",
            order.id,
            exc,
        )
        unknown_result = {
            "trade_state": "UNKNOWN",
            "requires_query": True,
            "error_message": "微信付款码状态未知，请稍后查单确认后再处理",
        }
        return order, unknown_result

    trade_state = result.get("trade_state")
    if trade_state == "SUCCESS":
        await mark_order_paid(
            db,
            order,
            payment_no=result.get("transaction_id") or f"WXCODE_{order.order_no}",
            payment_method="wechat_pay",
        )
        session.status = "paid"
    else:
        result["requires_query"] = True
        session.status = "pending_payment"
    audit_data = dict(session.audit_data or {})
    audit_data.update({
        "wechat_trade_state": trade_state,
        "wechat_transaction_id": result.get("transaction_id"),
    })
    session.audit_data = audit_data
    await db.flush()
    return order, result


async def query_temporary_codepay_result(
    db: AsyncSession,
    *,
    site_id: int,
    session_id: int,
    operator_id: int,
    operator_source: str,
) -> Tuple[TemporaryOrderSession, Order, Dict[str, Any]]:
    """查询现场付款码交易状态，并把成功支付补偿落库。"""
    result = await db.execute(
        select(TemporaryOrderSession)
        .where(
            TemporaryOrderSession.id == session_id,
            TemporaryOrderSession.site_id == site_id,
            TemporaryOrderSession.is_deleted.is_(False),
        )
        .with_for_update()
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40472, "message": "现场收款会话不存在"},
        )
    if session.payment_flow != "merchant_scan_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40073, "message": "仅付款码收款会话支持查单"},
        )
    if not session.order_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40973, "message": "现场收款尚未生成正式订单"},
        )

    order = await get_order_detail(db, session.order_id)
    if order.site_id != site_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "订单不存在"},
        )

    pay_result = await wechat_pay_service.query_codepay_transaction(order, site_id=site_id)
    trade_state = pay_result.get("trade_state")
    if trade_state == "SUCCESS":
        await mark_order_paid(
            db,
            order,
            payment_no=pay_result.get("transaction_id") or f"WXCODE_{order.order_no}",
            payment_method="wechat_pay",
            allow_expired=True,
        )
        session.status = "paid"
    elif trade_state in {"PAYERROR", "REVOKED", "CLOSED", "REFUND"}:
        session.status = "failed"
        pay_result["requires_query"] = False
    else:
        session.status = "pending_payment"
        pay_result["requires_query"] = True

    audit_data = dict(session.audit_data or {})
    audit_data.update({
        "wechat_trade_state": trade_state,
        "wechat_transaction_id": pay_result.get("transaction_id"),
        "last_query_at": datetime.now(timezone.utc).isoformat(),
        "last_query_by": {"id": operator_id, "source": operator_source},
    })
    session.audit_data = audit_data
    await db.flush()
    return session, order, pay_result


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
        await _release_order_item_inventory(db, item, order.id)

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
            await _refund_order_item_inventory(db, item, order.id)

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
        if order.payment_method == "wechat_pay":
            await wechat_pay_service.create_refund(
                order,
                refund_amount=order.actual_amount,
                reason=order.remark,
                site_id=order.site_id,
            )
            order.status = "refund_pending"
        else:
            order.status = "refunded"
            order.payment_status = "refunded"

            # 释放库存
            for item in order.items:
                item.refund_status = "refunded"
                await _refund_order_item_inventory(db, item, order.id)
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
        for item in order.items:
            await _release_order_item_inventory(db, item, order.id)
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40904, "message": "支付超时，订单已取消"},
        )

    if success:
        await mark_order_paid(
            db,
            order,
            payment_no=f"MOCK_{order.order_no}",
            payment_method="mock_pay",
        )
    else:
        order.status = "cancelled"
        order.remark = "模拟支付失败"
        # 释放库存
        for item in order.items:
            await _release_order_item_inventory(db, item, order.id)

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
        for item in order.items:
            await _release_order_item_inventory(db, item, order.id)
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40904, "message": "支付超时"},
        )

    try:
        payment_params = await wechat_pay_service.create_jsapi_prepay(order, site_id=order.site_id)
    except wechat_pay_service.WechatPayError as exc:
        logger.error("[微信支付] 发起支付失败: order_id=%s, error=%s", order_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": 50201, "message": "微信支付暂不可用，请稍后重试"},
        ) from exc

    order.payment_method = payment_method
    await db.flush()
    return payment_params


async def mark_order_paid(
    db: AsyncSession,
    order: Order,
    payment_no: str,
    payment_method: str = "wechat_pay",
    *,
    allow_expired: bool = False,
) -> Order:
    """将订单标记为已支付，确认库存并生成电子票。"""
    if order.payment_status == "paid":
        if order.order_type == "annual_card":
            await member_service.activate_annual_card_for_paid_order(db, order)
            await db.flush()
        return order
    if (
        allow_expired
        and order.status == "cancelled"
        and order.payment_status == "unpaid"
    ):
        order.remark = f"{order.remark or ''} 微信支付成功通知恢复超时订单".strip()
        await _relock_released_order_inventory_for_payment(db, order)
    elif order.status != "pending_payment" or order.payment_status != "unpaid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40902, "message": "订单状态不允许支付确认"},
        )
    if order.expire_at and datetime.now(timezone.utc) > order.expire_at and not allow_expired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40904, "message": "订单已超时，支付确认被拒绝"},
        )

    order.status = "paid"
    order.payment_status = "paid"
    order.payment_time = datetime.now(timezone.utc)
    order.payment_no = payment_no
    order.payment_method = payment_method

    for item in order.items:
        await _confirm_order_item_inventory(db, item, order.id)

    await settlement_service.record_payment_pending_income(db, order)
    if order.order_type == "annual_card":
        await member_service.activate_annual_card_for_paid_order(db, order)
    else:
        await _generate_tickets(db, order)
    await db.flush()
    return order


async def _relock_released_order_inventory_for_payment(db: AsyncSession, order: Order) -> None:
    """晚到微信成功通知恢复已取消订单时，先把已释放库存重新锁定。"""
    for item in order.items:
        quantity = getattr(item, "quantity", 1) or 1
        inventory_pool_id = getattr(item, "inventory_pool_id", None)
        if inventory_pool_id:
            await inventory_pool_service.lock_pool_inventory(
                db,
                pool_id=inventory_pool_id,
                quantity=quantity,
            )
            continue
        if getattr(item, "date", None):
            await inventory_service.lock_inventory(
                db,
                item.product_id,
                item.date,
                quantity,
                order.id,
                getattr(item, "sku_id", None),
                getattr(item, "time_slot", None),
            )
        elif getattr(item, "sku_id", None):
            await _lock_static_sku_stock(
                db,
                await _get_order_item_product(db, item.product_id),
                item.sku_id,
                quantity,
                [],
            )


async def settle_completed_order(
    db: AsyncSession,
    order: Order,
    *,
    trigger_type: str = "manual",
):
    """手动或补偿触发 completed 订单资金结算。"""
    if order.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40931, "message": "仅已完成订单可结算"},
        )
    return await settlement_service.settle_completed_order(
        db,
        order,
        trigger_type=trigger_type,
    )


async def handle_wechat_payment_notification(
    db: AsyncSession,
    transaction: Dict[str, Any],
) -> Optional[Order]:
    """处理微信支付成功通知。"""
    out_trade_no = transaction.get("out_trade_no")
    transaction_id = transaction.get("transaction_id")
    trade_state = transaction.get("trade_state")
    if not out_trade_no or trade_state != "SUCCESS":
        return None

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_no == out_trade_no, Order.is_deleted.is_(False))
        .with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        return None

    _validate_wechat_payment_transaction(order, transaction)
    return await mark_order_paid(
        db,
        order,
        payment_no=transaction_id or f"WX_{out_trade_no}",
        payment_method="wechat_pay",
        allow_expired=True,
    )


def _validate_wechat_payment_transaction(order: Order, transaction: Dict[str, Any]) -> None:
    config = wechat_pay_service.get_wechat_pay_config(order.site_id)
    if transaction.get("appid") and transaction.get("appid") != config.app_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40051, "message": "微信支付通知 appid 不匹配"},
        )
    if transaction.get("mchid") and transaction.get("mchid") != config.mch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40052, "message": "微信支付通知 mchid 不匹配"},
        )
    paid_total = ((transaction.get("amount") or {}).get("payer_total")
                  or (transaction.get("amount") or {}).get("total"))
    if paid_total is not None:
        expected_total = int((Decimal(str(order.actual_amount)).quantize(Decimal("0.01"))) * 100)
        if int(paid_total) != expected_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40053, "message": "微信支付通知金额不匹配"},
            )


async def handle_wechat_refund_notification(
    db: AsyncSession,
    refund: Dict[str, Any],
) -> Optional[Order]:
    """处理微信退款通知。"""
    out_trade_no = refund.get("out_trade_no")
    if not out_trade_no:
        return None

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_no == out_trade_no, Order.is_deleted.is_(False))
    )
    order = result.scalar_one_or_none()
    if order is None:
        return None

    refund_status = refund.get("refund_status") or refund.get("status")
    if refund_status == "SUCCESS":
        order.status = "refunded"
        order.payment_status = "refunded"
        order.refunded_amount = order.actual_amount
        for item in order.items:
            item.refund_status = "refunded"
            await _refund_order_item_inventory(db, item, order.id)
    elif refund_status in {"ABNORMAL", "CLOSED"}:
        order.status = "paid"
        order.payment_status = "paid"

    await db.flush()
    return order


async def seckill_order(
    db: AsyncSession,
    user: User,
    product_id: int,
    booking_date: date,
    quantity: int = 1,
    sku_id: Optional[int] = None,
    time_slot: Optional[str] = None,
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
    stock_key = f"seckill_stock:{product_id}:{booking_date}:{sku_id or 0}:{time_slot or ''}"
    user_key = f"seckill_user:{product_id}:{booking_date}:{sku_id or 0}:{time_slot or ''}:{user.id}"

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
        "time_slot": time_slot,
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
    site_id: Optional[int] = None,
) -> Order:
    """获取订单详情

    Args:
        db: 数据库会话
        order_id: 订单ID
        user_id: 用户ID（为None则不校验归属）
        site_id: 营地ID（为None则不校验营地）

    Returns:
        Order 实例
    """
    query = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .where(Order.id == order_id, Order.is_deleted.is_(False))
    )
    if user_id:
        query = query.where(Order.user_id == user_id)
    if site_id is not None:
        query = query.where(Order.site_id == site_id)

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40402, "message": "订单不存在"},
        )

    await _attach_order_display_fields(db, [order])
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
    product_id: Optional[int] = None,
    sku_id: Optional[int] = None,
    product_type: Optional[str] = None,
    booking_date_start: Optional[date] = None,
    booking_date_end: Optional[date] = None,
    time_slot: Optional[str] = None,
    payment_time_start: Optional[datetime] = None,
    payment_time_end: Optional[datetime] = None,
    amount_min: Optional[Decimal] = None,
    amount_max: Optional[Decimal] = None,
    verify_status: Optional[str] = None,
    source_channel: Optional[str] = None,
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
    query = build_order_list_query(
        site_id=site_id,
        user_id=user_id,
        order_status=order_status,
        order_type=order_type,
        date_start=date_start,
        date_end=date_end,
        keyword=keyword,
        payment_status=payment_status,
        product_id=product_id,
        sku_id=sku_id,
        product_type=product_type,
        booking_date_start=booking_date_start,
        booking_date_end=booking_date_end,
        time_slot=time_slot,
        payment_time_start=payment_time_start,
        payment_time_end=payment_time_end,
        amount_min=amount_min,
        amount_max=amount_max,
        verify_status=verify_status,
        source_channel=source_channel,
    )

    distinct_order_ids = query.with_only_columns(Order.id).order_by(None).distinct().subquery()

    # 总数：按订单去重，避免一单多商品/多票导致 total 放大。
    count_query = select(func.count()).select_from(distinct_order_ids)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序（白名单校验）
    id_query = select(distinct_order_ids.c.id).join(Order, Order.id == distinct_order_ids.c.id)
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        order_col = getattr(Order, sort_by)
        id_query = id_query.order_by(order_col.desc() if sort_order == "desc" else order_col.asc())
        if sort_by != "id":
            id_query = id_query.order_by(Order.id.desc())
    else:
        id_query = id_query.order_by(Order.id.desc())

    # 分页
    offset = (page - 1) * page_size
    id_query = id_query.offset(offset).limit(page_size)

    id_result = await db.execute(id_query)
    order_ids = list(id_result.scalars().all())
    if not order_ids:
        return [], total

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .where(Order.id.in_(order_ids), Order.is_deleted.is_(False))
    )
    orders_by_id = {order.id: order for order in result.scalars().unique().all()}
    orders = [orders_by_id[order_id] for order_id in order_ids if order_id in orders_by_id]

    await _attach_order_display_fields(db, orders)
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

async def _quote_inventory_for_order_item(
    db: AsyncSession,
    *,
    site_id: int,
    product_id: int,
    sku_id: Optional[int],
    inv_date: Optional[date],
    quantity: int,
    time_slot: Optional[str],
    pool_requirements: Dict[int, int],
    inventory_requirements: Dict[Tuple[int, int, Any, str], int],
) -> Tuple[str, Optional[int], Optional[int]]:
    """报价阶段校验库存，不改变库存数量。"""
    pool = await inventory_pool_service.get_bound_inventory_pool(
        db,
        site_id=site_id,
        product_id=product_id,
        sku_id=sku_id,
    )
    if pool:
        required_quantity = pool_requirements.get(pool.id, 0) + quantity
        try:
            inventory_pool_service.validate_pool_availability(
                pool,
                required_quantity=required_quantity,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 40901, "message": str(exc)},
            ) from exc
        pool_requirements[pool.id] = required_quantity
        return "inventory_pool", pool.id, int(pool.available)

    if inv_date is None:
        return "none", None, None

    query = select(Inventory).where(
        Inventory.product_id == product_id,
        Inventory.date == inv_date,
        Inventory.is_deleted.is_(False),
        Inventory.status == "open",
    )
    if sku_id is None:
        query = query.where(Inventory.sku_id.is_(None))
    else:
        query = query.where(Inventory.sku_id == sku_id)
    if time_slot is None:
        query = query.where(Inventory.time_slot.is_(None))
    else:
        query = query.where(Inventory.time_slot == time_slot)

    result = await db.execute(query)
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40404, "message": "库存记录不存在或已关闭"},
        )

    inventory_key = (product_id, sku_id or 0, inv_date, time_slot or "")
    required_quantity = inventory_requirements.get(inventory_key, 0) + quantity
    if inv.available < required_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": f"库存不足，可用: {inv.available}, 需要: {required_quantity}"},
        )
    inventory_requirements[inventory_key] = required_quantity
    return "inventory", None, int(inv.available)


async def _lock_inventory_for_order_item(
    db: AsyncSession,
    *,
    site_id: int,
    product_id: int,
    sku_id: Optional[int],
    inv_date: Optional[date],
    quantity: int,
    order_id: int,
    time_slot: Optional[str],
    locked_inventories: List[Tuple[int, Any, int, Any, Any]],
    locked_inventory_pools: List[Tuple[int, int]],
) -> Optional[int]:
    """优先锁定显式绑定的共享库存池，否则走旧日期库存。"""
    pool = await inventory_pool_service.get_bound_inventory_pool(
        db,
        site_id=site_id,
        product_id=product_id,
        sku_id=sku_id,
    )
    if pool:
        await inventory_pool_service.lock_pool_inventory(
            db,
            pool_id=pool.id,
            quantity=quantity,
        )
        locked_inventory_pools.append((pool.id, quantity))
        return pool.id

    if inv_date is None:
        return None

    await inventory_service.lock_inventory(
        db,
        product_id,
        inv_date,
        quantity,
        order_id,
        sku_id,
        time_slot,
    )
    locked_inventories.append((product_id, inv_date, quantity, sku_id, time_slot))
    return None


async def _lock_static_sku_stock(
    db: AsyncSession,
    product: Product,
    sku_id: int,
    quantity: int,
    locked_skus: List[Tuple[int, int]],
) -> SKU:
    """无日期且未绑定共享池的 SKU 商品，直接预扣 SKU.stock 防止绕过购物车超卖。"""
    result = await db.execute(
        select(SKU)
        .where(
            SKU.id == sku_id,
            SKU.product_id == product.id,
            SKU.is_deleted.is_(False),
            SKU.status == "active",
        )
        .with_for_update()
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "SKU不存在或已下架"},
        )
    if int(sku.stock or 0) < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": f"库存不足，可用: {sku.stock}, 需要: {quantity}"},
        )
    sku.stock = int(sku.stock or 0) - quantity
    locked_skus.append((sku_id, quantity))
    return sku


async def _quote_static_sku_stock(
    db: AsyncSession,
    product: Product,
    sku_id: int,
    quantity: int,
    sku_requirements: Dict[int, int],
) -> int:
    """报价阶段校验无日期 SKU 静态库存，不改变库存数量。"""
    result = await db.execute(
        select(SKU).where(
            SKU.id == sku_id,
            SKU.product_id == product.id,
            SKU.is_deleted.is_(False),
            SKU.status == "active",
        )
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "SKU不存在或已下架"},
        )
    available = int(sku.stock or 0)
    required_quantity = sku_requirements.get(sku_id, 0) + quantity
    if available < required_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 40901, "message": f"库存不足，可用: {available}, 需要: {required_quantity}"},
        )
    sku_requirements[sku_id] = required_quantity
    return available


async def _get_order_item_product(db: AsyncSession, product_id: int) -> Product:
    """根据订单项商品 ID 读取商品，用于无日期 SKU 库存恢复/重锁。"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted.is_(False))
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "商品不存在或已删除"},
        )
    return product


async def _release_static_sku_stock(
    db: AsyncSession,
    sku_id: int,
    quantity: int,
) -> None:
    """释放无日期 SKU 静态库存预扣。"""
    result = await db.execute(
        select(SKU)
        .where(SKU.id == sku_id, SKU.is_deleted.is_(False))
        .with_for_update()
    )
    sku = result.scalar_one_or_none()
    if sku is not None:
        sku.stock = int(sku.stock or 0) + quantity


async def _release_order_item_inventory(
    db: AsyncSession,
    item: OrderItem,
    order_id: int,
) -> None:
    """取消或支付失败：锁定库存回到可用。"""
    inventory_pool_id = getattr(item, "inventory_pool_id", None)
    if inventory_pool_id:
        await inventory_pool_service.release_pool_inventory(
            db,
            pool_id=inventory_pool_id,
            quantity=getattr(item, "quantity", 1) or 1,
        )
        return
    if getattr(item, "date", None):
        await inventory_service.release_inventory(
            db,
            item.product_id,
            item.date,
            getattr(item, "quantity", 1) or 1,
            order_id,
            getattr(item, "sku_id", None),
            getattr(item, "time_slot", None),
        )
    elif getattr(item, "sku_id", None):
        await _release_static_sku_stock(db, item.sku_id, getattr(item, "quantity", 1) or 1)


async def _confirm_order_item_inventory(
    db: AsyncSession,
    item: OrderItem,
    order_id: int,
) -> None:
    """支付成功：锁定库存转已售。"""
    inventory_pool_id = getattr(item, "inventory_pool_id", None)
    if inventory_pool_id:
        await inventory_pool_service.confirm_pool_sell(
            db,
            pool_id=inventory_pool_id,
            quantity=getattr(item, "quantity", 1) or 1,
        )
        return
    if getattr(item, "date", None):
        await inventory_service.confirm_sell(
            db,
            item.product_id,
            item.date,
            getattr(item, "quantity", 1) or 1,
            order_id,
            getattr(item, "sku_id", None),
            getattr(item, "time_slot", None),
        )


async def _refund_order_item_inventory(
    db: AsyncSession,
    item: OrderItem,
    order_id: int,
    *,
    quantity: Optional[int] = None,
) -> None:
    """退款成功：已售库存回补可用。"""
    refund_quantity = quantity or getattr(item, "quantity", 1) or 1
    inventory_pool_id = getattr(item, "inventory_pool_id", None)
    if inventory_pool_id:
        await inventory_pool_service.refund_pool_inventory(
            db,
            pool_id=inventory_pool_id,
            quantity=refund_quantity,
        )
        return
    if getattr(item, "date", None):
        await _refund_inventory(
            db,
            item.product_id,
            item.date,
            refund_quantity,
            order_id,
            getattr(item, "sku_id", None),
            getattr(item, "time_slot", None),
        )
    elif getattr(item, "sku_id", None):
        await _release_static_sku_stock(db, item.sku_id, refund_quantity)


async def _get_user_order(db: AsyncSession, order_id: int, user_id: int) -> Order:
    """获取用户的订单（带权限校验）"""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
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
        qr_token = generate_qr_token()
        ticket = Ticket(
            site_id=order.site_id,
            order_id=order.id,
            order_item_id=item.id,
            user_id=order.user_id,
            ticket_no=generate_ticket_code(),
            ticket_type=ticket_type,
            qr_token_hash=ticket_service._hash_qr_token(qr_token),
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
    if sku_id is None:
        query = query.where(Inventory.sku_id.is_(None))
    else:
        query = query.where(Inventory.sku_id == sku_id)
    if time_slot is None:
        query = query.where(Inventory.time_slot.is_(None))
    else:
        query = query.where(Inventory.time_slot == time_slot)

    result = await db.execute(query.with_for_update())
    inv = result.scalar_one_or_none()

    if inv:
        if inv.sold < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 40907, "message": f"库存已售数量不足，已售: {inv.sold}, 需要退款: {quantity}"},
            )
        inv.sold -= quantity
        inv.available += quantity

        log = InventoryLog(
            inventory_id=inv.id,
            change_type="refund",
            quantity=quantity,
            order_id=order_id,
            remark=f"退款恢复 order_id={order_id}",
        )
        db.add(log)


async def _resolve_price(
    db: AsyncSession,
    product: Product,
    target_date: date,
    sku_id: Optional[int] = None,
) -> Decimal:
    """4级优先级链动态定价

    1. SKU价格（如有，最高优先级）
    2. 特定日期特殊价
    3. 自定义日期类型价（DateTypeConfig 配置的日期类型）
    4. 系统日期类型价（自动判断 weekday/weekend）
    5. 商品基础价（兜底）

    Args:
        db: 数据库会话
        product: 商品实例
        target_date: 目标日期

    Returns:
        当天适用价格
    """
    # 1. SKU 价格优先，保证商品详情、报价、建单三端同价
    if sku_id:
        return await _resolve_sku_price(db, product, sku_id)

    # 2. 特定日期特殊价
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

    # 3. 自定义日期类型价（查 DateTypeConfig）
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

    # 4. 系统日期类型价（周一~周五=weekday, 周六日=weekend）
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

    # 5. 商品基础价（兜底）
    logger.info(
        f"[定价] 使用基础价: product={product.id}, date={target_date}, "
        f"price={product.base_price}"
    )
    return product.base_price


async def _resolve_sku_price(
    db: AsyncSession,
    product: Product,
    sku_id: Optional[int],
) -> Decimal:
    """非营位商品价格解析：SKU 价格优先，商品基础价兜底。"""
    if not sku_id:
        return product.base_price or Decimal("0")

    result = await db.execute(
        select(SKU).where(
            SKU.id == sku_id,
            SKU.product_id == product.id,
            SKU.is_deleted.is_(False),
            SKU.status == "active",
        )
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "SKU不存在或已下架"},
        )
    return sku.price or Decimal("0")


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
