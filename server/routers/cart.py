"""
购物车路由

- GET / — 购物车列表
- POST /items — 添加商品
- PUT /items/{id} — 修改数量
- DELETE /items/{id} — 删除商品
- POST /checkout — 结算
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from middleware.auth import get_current_user
from models.inventory_pool import InventoryPool, InventoryPoolBinding
from models.order import Cart, CartItem
from models.product import Product, ProductStatus, SKU, SKUStatus
from models.user import User
from schemas.cart import CartAddItemRequest, CartCheckoutRequest
from schemas.common import ResponseModel
from services import inventory_pool_service, order_service

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


async def _validate_cart_sku_stock(
    db: AsyncSession,
    *,
    product: Product,
    sku: SKU,
    quantity: int,
) -> None:
    """校验购物车 SKU 库存；共享库存池命中时以库存池为事实源。"""
    pool = await inventory_pool_service.get_bound_inventory_pool(
        db,
        site_id=product.site_id,
        product_id=product.id,
        sku_id=sku.id,
    )
    if pool:
        try:
            inventory_pool_service.validate_pool_availability(pool, required_quantity=quantity)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": 40004, "message": str(exc)},
            ) from exc
        return
    if sku.stock < quantity:
        raise HTTPException(
            status_code=400,
            detail={"code": 40004, "message": f"库存不足，当前库存: {sku.stock}"},
        )


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

    sku_pool_map: Dict[int, InventoryPool] = {}
    if sku_ids and products_map:
        expected_pool_code_by_sku: Dict[int, str] = {}
        for sku_id, sku in skus_map.items():
            product = products_map.get(sku.product_id)
            if product:
                expected_pool_code_by_sku[sku_id] = inventory_pool_service.get_product_sku_shared_pool_code(product.site_id, product.id)
        sku_pool_conditions = [
            and_(InventoryPoolBinding.sku_id == sku_id, InventoryPool.pool_code == pool_code)
            for sku_id, pool_code in expected_pool_code_by_sku.items()
        ]
        pool_result = await db.execute(
            select(InventoryPoolBinding.sku_id, InventoryPool)
            .join(InventoryPool, InventoryPool.id == InventoryPoolBinding.inventory_pool_id)
            .where(
                or_(*sku_pool_conditions),
                InventoryPoolBinding.status == "active",
                InventoryPoolBinding.is_deleted.is_(False),
                InventoryPool.status == "active",
                InventoryPool.is_deleted.is_(False),
            )
            .order_by(InventoryPoolBinding.priority.asc(), InventoryPoolBinding.id.asc())
        ) if sku_pool_conditions else None
        if pool_result:
            for sku_id, pool in pool_result.all():
                if sku_id is not None and int(sku_id) not in sku_pool_map:
                    sku_pool_map[int(sku_id)] = pool

    items_data = []
    total_count = 0
    total_price = Decimal("0")

    for item in cart_items:
        product = products_map.get(item.product_id)
        sku = skus_map.get(item.sku_id) if item.sku_id else None

        # 确定价格和库存状态
        if sku:
            price = sku.price
            pool = sku_pool_map.get(sku.id)
            stock = int(pool.available) if pool else int(sku.stock)
            stock_available = stock > 0
            image = sku.image_url or (product.images[0]["url"] if product and product.images else None)
        elif product:
            price = product.base_price
            stock_available = True  # 非SKU商品不按此处检查
            stock = product.stock or 0
            image = product.images[0]["url"] if product.images else None
        else:
            price = Decimal("0")
            stock_available = False
            stock = 0
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
            "stock": stock,
            "sku_spec_values": sku.spec_values if sku else None,
            "shipping_required": bool(getattr(product.ext_shop, "shipping_required", False)) if product else False,
        })

    return ResponseModel.success(data={
        "items": items_data,
        "summary": {
            "total_count": total_count,
            "total_price": str(total_price),
        },
    })


@router.post("/quote", summary="购物车报价")
async def quote_cart(
    item_ids: List[int] = Body(..., embed=True),
    disclaimer_signed: bool = Body(default=False, embed=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """购物车确认页报价：复用订单服务真实价格、库存和优惠。"""
    cart = await _get_or_create_cart(db, user.id)
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

    order_items_payload = [
        {
            "product_id": item.product_id,
            "sku_id": item.sku_id,
            "quantity": item.quantity,
            "dates": [],
        }
        for item in cart_items
    ]
    quote = await order_service.quote_order(
        db,
        user,
        order_items_payload,
        disclaimer_signed=disclaimer_signed,
    )
    return ResponseModel.success(data=quote)


@router.post("/items", summary="添加商品到购物车")
async def add_cart_item(
    body: CartAddItemRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """添加商品到购物车"""
    product_id = body.product_id
    sku_id = body.sku_id
    quantity = body.quantity

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
        await _validate_cart_sku_stock(db, product=product, sku=sku, quantity=quantity)

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
            if sku_obj:
                await _validate_cart_sku_stock(db, product=product, sku=sku_obj, quantity=new_quantity)
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
        product = await db.get(Product, cart_item.product_id)
        if sku and product:
            await _validate_cart_sku_stock(db, product=product, sku=sku, quantity=quantity)

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
    body: CartCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """购物车结算：生成预订单"""
    item_ids = body.item_ids
    address_id = body.address_id
    remark = body.remark
    disclaimer_signed = body.disclaimer_signed

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
            await _validate_cart_sku_stock(db, product=product, sku=sku, quantity=item.quantity)

    # 按商品类型（order_type）分组拆单，并复用订单服务统一锁库存/计价/站点隔离。
    type_groups: Dict[str, List[CartItem]] = defaultdict(list)
    for item in cart_items:
        product = products_map[item.product_id]
        order_type = product.type  # Product.type 即为订单的 order_type
        type_groups[order_type].append(item)

    created_orders = []
    for items_in_group in type_groups.values():
        order_items_payload = [
            {
                "product_id": item.product_id,
                "sku_id": item.sku_id,
                "quantity": item.quantity,
                "dates": [],
            }
            for item in items_in_group
        ]
        order = await order_service.create_order(
            db,
            user,
            order_items_payload,
            address_id=address_id,
            remark=remark,
            disclaimer_signed=disclaimer_signed,
            payment_method="wechat_pay",
            source_channel="cart",
        )
        created_orders.append(order)

    # 清除购物车中已结算的 items（软删除）
    for item in cart_items:
        item.is_deleted = True

    await db.commit()

    return ResponseModel.success(
        data={
            "order_no": created_orders[0].order_no,
            "order_ids": [order.id for order in created_orders],
        },
        message="结算完成",
    )
