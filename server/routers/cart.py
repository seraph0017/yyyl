"""
购物车路由

- GET / — 购物车列表
- POST /items — 添加商品
- PUT /items/{id} — 修改数量
- DELETE /items/{id} — 删除商品
- POST /checkout — 结算
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from middleware.auth import get_current_user
from models.order import Cart, CartItem, Order, OrderItem, OrderStatus, PaymentStatus
from models.product import Product, ProductStatus, SKU, SKUStatus
from models.user import User
from schemas.common import ResponseModel
from utils.helpers import generate_order_no

router = APIRouter(prefix="/api/v1/cart", tags=["购物车"])


async def _get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
    """查找或创建用户的购物车（一个用户一个Cart）"""
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.items))
        .where(Cart.user_id == user_id, Cart.is_deleted.is_(False))
    )
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
    return cart


@router.get("/", summary="购物车列表")
async def list_cart_items(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的购物车列表"""
    cart = await _get_or_create_cart(db, user.id)

    # 查询购物车项，同时加载关联的 Product 和 SKU
    result = await db.execute(
        select(CartItem)
        .where(CartItem.cart_id == cart.id, CartItem.is_deleted.is_(False))
    )
    cart_items = result.scalars().all()

    # 批量加载商品和SKU信息
    product_ids = [item.product_id for item in cart_items]
    sku_ids = [item.sku_id for item in cart_items if item.sku_id]

    products_map: Dict[int, Product] = {}
    skus_map: Dict[int, SKU] = {}

    if product_ids:
        prod_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        for p in prod_result.scalars().all():
            products_map[p.id] = p

    if sku_ids:
        sku_result = await db.execute(
            select(SKU).where(SKU.id.in_(sku_ids))
        )
        for s in sku_result.scalars().all():
            skus_map[s.id] = s

    items_data = []
    total_count = 0
    total_price = Decimal("0")

    for item in cart_items:
        product = products_map.get(item.product_id)
        sku = skus_map.get(item.sku_id) if item.sku_id else None

        # 确定价格和库存状态
        if sku:
            price = sku.price
            stock_available = sku.stock > 0
            image = sku.image_url or (product.images[0]["url"] if product and product.images else None)
        elif product:
            price = product.base_price
            stock_available = True  # 非SKU商品不按此处检查
            image = product.images[0]["url"] if product.images else None
        else:
            price = Decimal("0")
            stock_available = False
            image = None

        item_total = price * item.quantity
        total_count += item.quantity
        if item.checked:
            total_price += item_total

        items_data.append({
            "id": item.id,
            "product_id": item.product_id,
            "sku_id": item.sku_id,
            "quantity": item.quantity,
            "checked": item.checked,
            "product_name": product.name if product else None,
            "product_type": product.type if product else None,
            "product_status": product.status if product else None,
            "image": image,
            "price": str(price),
            "item_total": str(item_total),
            "stock_available": stock_available,
            "sku_spec_values": sku.spec_values if sku else None,
        })

    return ResponseModel.success(data={
        "items": items_data,
        "summary": {
            "total_count": total_count,
            "total_price": str(total_price),
        },
    })


@router.post("/items", summary="添加商品到购物车")
async def add_cart_item(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """添加商品到购物车"""
    product_id: int = body.get("product_id")
    sku_id: Optional[int] = body.get("sku_id")
    quantity: int = body.get("quantity", 1)

    if not product_id or quantity < 1:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "参数错误：product_id 和 quantity 必填且 quantity >= 1"},
        )

    # 校验商品存在且在售
    product = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted.is_(False),
        )
    )
    product = product.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=404,
            detail={"code": 40401, "message": "商品不存在"},
        )
    if product.status != ProductStatus.ON_SALE.value:
        raise HTTPException(
            status_code=400,
            detail={"code": 40002, "message": "商品未在售"},
        )

    # 如果指定了SKU，校验SKU存在并检查库存
    if sku_id:
        sku = await db.execute(
            select(SKU).where(
                SKU.id == sku_id,
                SKU.product_id == product_id,
                SKU.is_deleted.is_(False),
            )
        )
        sku = sku.scalar_one_or_none()
        if not sku:
            raise HTTPException(
                status_code=404,
                detail={"code": 40402, "message": "SKU不存在"},
            )
        if sku.status != SKUStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail={"code": 40003, "message": "该规格已下架"},
            )
        if sku.stock < quantity:
            raise HTTPException(
                status_code=400,
                detail={"code": 40004, "message": f"库存不足，当前库存: {sku.stock}"},
            )

    # 获取或创建购物车
    cart = await _get_or_create_cart(db, user.id)

    # 查找是否已有相同商品+SKU的条目
    existing_result = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id,
            CartItem.sku_id == sku_id if sku_id else CartItem.sku_id.is_(None),
            CartItem.is_deleted.is_(False),
        )
    )
    existing_item = existing_result.scalar_one_or_none()

    if existing_item:
        new_quantity = existing_item.quantity + quantity
        # 再次校验库存
        if sku_id:
            sku_obj = await db.get(SKU, sku_id)
            if sku_obj and sku_obj.stock < new_quantity:
                raise HTTPException(
                    status_code=400,
                    detail={"code": 40004, "message": f"库存不足，当前库存: {sku_obj.stock}"},
                )
        existing_item.quantity = new_quantity
    else:
        new_item = CartItem(
            cart_id=cart.id,
            product_id=product_id,
            sku_id=sku_id,
            quantity=quantity,
            checked=True,
        )
        db.add(new_item)

    await db.commit()
    return ResponseModel.success(data=None, message="已添加到购物车")


@router.put("/items/{item_id}", summary="修改购物车商品数量")
async def update_cart_item(
    item_id: int,
    quantity: int = Body(..., ge=1, embed=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修改购物车中商品的数量"""
    # 获取购物车
    cart = await _get_or_create_cart(db, user.id)

    # 查找 CartItem 并验证属于当前用户
    result = await db.execute(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart.id,
            CartItem.is_deleted.is_(False),
        )
    )
    cart_item = result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail={"code": 40403, "message": "购物车商品不存在"},
        )

    # 校验库存
    if cart_item.sku_id:
        sku = await db.get(SKU, cart_item.sku_id)
        if sku and sku.stock < quantity:
            raise HTTPException(
                status_code=400,
                detail={"code": 40004, "message": f"库存不足，当前库存: {sku.stock}"},
            )

    cart_item.quantity = quantity
    await db.commit()
    return ResponseModel.success(data=None, message="数量已更新")


@router.delete("/items/{item_id}", summary="删除购物车商品")
async def delete_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从购物车中删除商品"""
    cart = await _get_or_create_cart(db, user.id)

    result = await db.execute(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart.id,
            CartItem.is_deleted.is_(False),
        )
    )
    cart_item = result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail={"code": 40403, "message": "购物车商品不存在"},
        )

    cart_item.is_deleted = True
    await db.commit()
    return ResponseModel.success(data=None, message="已从购物车移除")


@router.post("/checkout", summary="购物车结算")
async def checkout(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """购物车结算：生成预订单"""
    item_ids: List[int] = body.get("item_ids", [])
    address_id: Optional[int] = body.get("address_id")
    remark: Optional[str] = body.get("remark")

    if not item_ids:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "请选择要结算的商品"},
        )

    # 获取购物车
    cart = await _get_or_create_cart(db, user.id)

    # 查询选中的 CartItem
    result = await db.execute(
        select(CartItem).where(
            CartItem.id.in_(item_ids),
            CartItem.cart_id == cart.id,
            CartItem.is_deleted.is_(False),
        )
    )
    cart_items = result.scalars().all()

    if not cart_items:
        raise HTTPException(
            status_code=400,
            detail={"code": 40001, "message": "未找到选中的购物车商品"},
        )

    # 加载商品和SKU信息
    product_ids = list({item.product_id for item in cart_items})
    sku_ids = [item.sku_id for item in cart_items if item.sku_id]

    prod_result = await db.execute(
        select(Product).where(Product.id.in_(product_ids), Product.is_deleted.is_(False))
    )
    products_map: Dict[int, Product] = {p.id: p for p in prod_result.scalars().all()}

    skus_map: Dict[int, SKU] = {}
    if sku_ids:
        sku_result = await db.execute(
            select(SKU).where(SKU.id.in_(sku_ids), SKU.is_deleted.is_(False))
        )
        skus_map = {s.id: s for s in sku_result.scalars().all()}

    # 校验所有商品在售
    for item in cart_items:
        product = products_map.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=400,
                detail={"code": 40002, "message": f"商品(ID:{item.product_id})不存在或已下架"},
            )
        if product.status != ProductStatus.ON_SALE.value:
            raise HTTPException(
                status_code=400,
                detail={"code": 40002, "message": f"商品「{product.name}」已下架"},
            )
        # SKU 库存校验
        if item.sku_id:
            sku = skus_map.get(item.sku_id)
            if not sku or sku.status != SKUStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=400,
                    detail={"code": 40003, "message": f"商品「{product.name}」规格已失效"},
                )
            if sku.stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail={"code": 40004, "message": f"商品「{product.name}」库存不足"},
                )

    # 按商品类型（order_type）分组拆单
    type_groups: Dict[str, List[CartItem]] = defaultdict(list)
    for item in cart_items:
        product = products_map[item.product_id]
        order_type = product.type  # Product.type 即为订单的 order_type
        type_groups[order_type].append(item)

    now = datetime.now(timezone.utc)

    if len(type_groups) == 1:
        # 只有一种类型，直接创建单个订单（无需父子关系）
        order_type = list(type_groups.keys())[0]
        items_in_group = list(type_groups.values())[0]

        total_amount = Decimal("0")
        order_items_to_add = []
        for ci in items_in_group:
            product = products_map[ci.product_id]
            sku = skus_map.get(ci.sku_id) if ci.sku_id else None
            unit_price = sku.price if sku else product.base_price
            item_total = unit_price * ci.quantity
            total_amount += item_total

            order_items_to_add.append({
                "product_id": ci.product_id,
                "sku_id": ci.sku_id,
                "quantity": ci.quantity,
                "unit_price": unit_price,
                "actual_price": unit_price,
            })

        # 获取支付超时
        first_product = products_map[items_in_group[0].product_id]
        timeout_seconds = first_product.normal_payment_timeout

        order = Order(
            order_no=generate_order_no(),
            user_id=user.id,
            order_type=order_type,
            status=OrderStatus.PENDING_PAYMENT.value,
            total_amount=total_amount,
            discount_amount=Decimal("0"),
            actual_amount=total_amount,
            payment_status=PaymentStatus.UNPAID.value,
            address_id=address_id,
            remark=remark,
            expire_at=now + timedelta(seconds=timeout_seconds),
            site_id=user.site_id,
        )
        db.add(order)
        await db.flush()

        for oi_data in order_items_to_add:
            oi = OrderItem(
                order_id=order.id,
                product_id=oi_data["product_id"],
                sku_id=oi_data["sku_id"],
                quantity=oi_data["quantity"],
                unit_price=oi_data["unit_price"],
                actual_price=oi_data["actual_price"],
            )
            db.add(oi)

        created_order_ids = [order.id]
        parent_order_no = order.order_no
    else:
        # 多种类型，创建父订单 + 子订单
        parent_total = Decimal("0")

        parent_order = Order(
            order_no=generate_order_no(),
            user_id=user.id,
            order_type="mixed",
            status=OrderStatus.PENDING_PAYMENT.value,
            total_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            actual_amount=Decimal("0"),
            payment_status=PaymentStatus.UNPAID.value,
            address_id=address_id,
            remark=remark,
            expire_at=now + timedelta(seconds=1800),
            site_id=user.site_id,
        )
        db.add(parent_order)
        await db.flush()

        child_order_ids = []

        for order_type, items_in_group in type_groups.items():
            sub_total = Decimal("0")
            order_items_data = []

            for ci in items_in_group:
                product = products_map[ci.product_id]
                sku = skus_map.get(ci.sku_id) if ci.sku_id else None
                unit_price = sku.price if sku else product.base_price
                item_total = unit_price * ci.quantity
                sub_total += item_total

                order_items_data.append({
                    "product_id": ci.product_id,
                    "sku_id": ci.sku_id,
                    "quantity": ci.quantity,
                    "unit_price": unit_price,
                    "actual_price": unit_price,
                })

            child_order = Order(
                order_no=generate_order_no(),
                user_id=user.id,
                parent_order_id=parent_order.id,
                order_type=order_type,
                status=OrderStatus.PENDING_PAYMENT.value,
                total_amount=sub_total,
                discount_amount=Decimal("0"),
                actual_amount=sub_total,
                payment_status=PaymentStatus.UNPAID.value,
                address_id=address_id,
                remark=remark,
                expire_at=now + timedelta(seconds=1800),
                site_id=user.site_id,
            )
            db.add(child_order)
            await db.flush()

            for oi_data in order_items_data:
                oi = OrderItem(
                    order_id=child_order.id,
                    product_id=oi_data["product_id"],
                    sku_id=oi_data["sku_id"],
                    quantity=oi_data["quantity"],
                    unit_price=oi_data["unit_price"],
                    actual_price=oi_data["actual_price"],
                )
                db.add(oi)

            parent_total += sub_total
            child_order_ids.append(child_order.id)

        # 更新父订单金额
        parent_order.total_amount = parent_total
        parent_order.actual_amount = parent_total

        created_order_ids = child_order_ids
        parent_order_no = parent_order.order_no

    # 清除购物车中已结算的 items（软删除）
    for item in cart_items:
        item.is_deleted = True

    await db.commit()

    return ResponseModel.success(
        data={
            "order_no": parent_order_no,
            "order_ids": created_order_ids,
        },
        message="结算完成",
    )
