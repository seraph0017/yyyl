"""
v1.7 统一退款服务
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.finance import FinanceAccount, FinanceTransaction
from models.member import AnnualCard, AnnualCardConfig
from models.order import Order
from models.refund import RefundRecord, RefundRecordItem
from services import order_service, wechat_pay_service
from utils.helpers import generate_transaction_no


async def create_refund_record(
    db: AsyncSession,
    order: Order,
    *,
    refund_mode: str,
    order_action: str,
    refund_amount: Decimal,
    release_inventory: bool,
    reason: str,
    requested_by: int,
    requester_role: str = "admin",
    items: Optional[list[dict[str, Any]]] = None,
) -> RefundRecord:
    """创建退款记录并按订单处理策略更新订单/票/库存状态。"""
    locked_result = await db.execute(
        select(Order)
        .where(
            Order.id == order.id,
            Order.site_id == order.site_id,
            Order.is_deleted.is_(False),
        )
        .with_for_update()
    )
    locked_order = locked_result.scalar_one_or_none()
    if locked_order is not None:
        order = locked_order

    await _validate_order_refundable(db, order)
    _validate_refund_permission(
        refund_mode=refund_mode,
        order_action=order_action,
        requester_role=requester_role,
    )
    selected_items = _select_refund_items(order, refund_mode=refund_mode, items=items)
    system_amount = _calculate_system_amount(order, refund_mode=refund_mode, selected_items=selected_items)

    if refund_amount > _remaining_refundable_amount(order):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40041, "message": "退款金额不能超过订单可退金额"},
        )

    refund = RefundRecord(
        site_id=order.site_id,
        order_id=order.id,
        refund_no=generate_transaction_no("RF"),
        refund_mode=refund_mode,
        order_action=order_action,
        refund_amount=refund_amount,
        system_amount=system_amount,
        release_inventory=release_inventory,
        reason=reason,
        risk_level=_resolve_risk_level(order, refund_mode, order_action, refund_amount),
        status="pending",
        requested_by=requested_by,
    )
    db.add(refund)
    order.refund_status = "pending"

    for item in selected_items:
        item_amount = _resolve_item_refund_amount(item, items)
        refund_item = RefundRecordItem(
            refund_record=refund,
            order_item_id=item.id,
            refund_amount=item_amount,
            quantity=_resolve_item_refund_quantity(item, items),
            release_inventory=release_inventory,
        )
        db.add(refund_item)

    if order_action == "cancel_order":
        order.refund_status = "pending"

    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(refund)
    return refund


async def get_order_for_refund(
    db: AsyncSession,
    *,
    order_id: int,
    site_id: int,
) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.tickets))
        .where(
            Order.id == order_id,
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
        )
        .with_for_update()
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})
    return order


async def list_refunds(
    db: AsyncSession,
    *,
    site_id: int,
    order_id: Optional[int] = None,
    refund_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RefundRecord], int]:
    query = select(RefundRecord).where(
        RefundRecord.site_id == site_id,
        RefundRecord.is_deleted.is_(False),
    )
    if order_id:
        query = query.where(RefundRecord.order_id == order_id)
    if refund_status:
        query = query.where(RefundRecord.status == refund_status)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(
        query.order_by(RefundRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def find_pending_refund_for_order(
    db: AsyncSession,
    *,
    order_id: int,
    site_id: int,
) -> Optional[RefundRecord]:
    """查找订单当前可审批的退款记录，用于兼容旧审批入口的幂等处理。"""
    result = await db.execute(
        select(RefundRecord)
        .where(
            RefundRecord.order_id == order_id,
            RefundRecord.site_id == site_id,
            RefundRecord.status.in_(["pending", "processing"]),
            RefundRecord.is_deleted.is_(False),
        )
        .order_by(RefundRecord.created_at.desc())
    )
    return result.scalars().first()


async def get_refund_detail(
    db: AsyncSession,
    *,
    site_id: int,
    refund_id: int,
) -> RefundRecord:
    result = await db.execute(
        select(RefundRecord)
        .options(selectinload(RefundRecord.items))
        .where(
            RefundRecord.id == refund_id,
            RefundRecord.site_id == site_id,
            RefundRecord.is_deleted.is_(False),
        )
    )
    refund = result.scalar_one_or_none()
    if not refund:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "退款记录不存在"})
    return refund


async def approve_refund(
    db: AsyncSession,
    *,
    refund_id: int,
    site_id: int,
    approved_by: int,
) -> RefundRecord:
    refund = await get_refund_detail(db, site_id=site_id, refund_id=refund_id)
    if refund.status != "pending":
        raise HTTPException(status_code=400, detail={"code": 40941, "message": "退款记录状态不允许审批"})

    order = await _get_order_by_id(db, order_id=refund.order_id, site_id=site_id)
    if order.payment_method == "wechat_pay":
        result = await wechat_pay_service.create_refund(
            order,
            refund_amount=refund.refund_amount,
            reason=refund.reason,
            site_id=site_id,
            out_refund_no=refund.refund_no,
        )
        refund.status = "processing"
        refund.wechat_refund_id = result.get("refund_id") or result.get("refund_id".upper())
    else:
        refund.status = "approved"
        await apply_refund_success(db, refund)

    refund.approved_by = approved_by
    refund.approved_at = datetime.now(timezone.utc)
    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(refund)
    return refund


async def reject_refund(
    db: AsyncSession,
    *,
    refund_id: int,
    site_id: int,
    rejected_by: int,
    reason: str,
) -> RefundRecord:
    refund = await get_refund_detail(db, site_id=site_id, refund_id=refund_id)
    if refund.status != "pending":
        raise HTTPException(status_code=400, detail={"code": 40941, "message": "退款记录状态不允许拒绝"})
    order = await _get_order_by_id(db, order_id=refund.order_id, site_id=site_id)
    refund.status = "rejected"
    refund.approved_by = rejected_by
    refund.approved_at = datetime.now(timezone.utc)
    refund.reason = f"{refund.reason}\n拒绝原因: {reason}"
    order.refund_status = "rejected"
    await db.flush()
    if hasattr(db, "refresh"):
        await db.refresh(refund)
    return refund


async def handle_wechat_refund_notification(
    db: AsyncSession,
    payload: dict[str, Any],
) -> Optional[RefundRecord]:
    """处理微信退款成功通知，以 out_refund_no/refund_no 幂等更新退款记录。"""
    refund_no = payload.get("out_refund_no") or payload.get("refund_no")
    if not refund_no:
        return None

    result = await db.execute(
        select(RefundRecord).where(
            RefundRecord.refund_no == refund_no,
            RefundRecord.is_deleted.is_(False),
        ).with_for_update()
    )
    refund = result.scalar_one_or_none()
    if not refund:
        return None

    refund_status = payload.get("refund_status") or payload.get("status")
    if refund_status == "SUCCESS":
        await apply_refund_success(
            db,
            refund,
            wechat_refund_id=payload.get("refund_id"),
        )
    elif refund_status in {"ABNORMAL", "CLOSED"}:
        refund.status = "failed"
        order = await _get_order_by_id(db, order_id=refund.order_id, site_id=refund.site_id)
        order.refund_status = "rejected"

    await db.flush()
    return refund


async def apply_refund_success(
    db: AsyncSession,
    refund: RefundRecord,
    *,
    wechat_refund_id: Optional[str] = None,
) -> Optional[FinanceTransaction]:
    """退款成功后扣减财务账户并写退款流水，按退款记录幂等。"""
    if isinstance(refund, RefundRecord):
        locked_result = await db.execute(
            select(RefundRecord)
            .where(
                RefundRecord.id == refund.id,
                RefundRecord.site_id == refund.site_id,
                RefundRecord.is_deleted.is_(False),
            )
            .with_for_update()
        )
        locked_refund = locked_result.scalar_one_or_none()
        if locked_refund is not None:
            refund = locked_refund

    existing = await _find_existing_refund_tx(db, refund_id=refund.id, site_id=refund.site_id)
    if existing or _is_refund_success_already_applied(refund):
        order = await _get_order_by_id(db, order_id=refund.order_id, site_id=refund.site_id)
        refund.status = "completed"
        refund.completed_at = refund.completed_at or datetime.now(timezone.utc)
        if getattr(order, "refund_status", None) not in {"refunded", "partial"}:
            order.refund_status = "refunded"
        if getattr(refund, "order_action", None) == "cancel_order":
            order.status = "cancelled"
            order.payment_status = "refunded"
        if wechat_refund_id:
            refund.wechat_refund_id = wechat_refund_id
        await db.flush()
        return existing

    order = await _get_order_by_id(db, order_id=refund.order_id, site_id=refund.site_id)
    account = await _get_finance_account(db, site_id=refund.site_id)
    amount = Decimal(str(refund.refund_amount))
    account_type = _resolve_refund_account_type(order)

    if account_type == "available":
        account.available_amount -= amount
    else:
        account.pending_amount -= amount

    tx = FinanceTransaction(
        transaction_no=generate_transaction_no("RF"),
        order_id=refund.order_id,
        type="refund",
        amount=amount,
        account_type=account_type,
        from_account=account_type,
        to_account="user",
        status="completed",
        remark=f"退款成功 refund_id={refund.id}",
        site_id=refund.site_id,
        refund_record_id=refund.id,
    )
    db.add(tx)
    selected_items = _select_order_items_for_refund_record(order, refund)
    if not getattr(refund, "inventory_released", False):
        await _release_refund_record_inventory(db, refund, order=order, selected_items=selected_items)
    _apply_refund_record_to_order(order, refund, selected_items=selected_items)
    refund.status = "completed"
    order.refund_status = "refunded"
    if getattr(refund, "release_inventory", False):
        _void_tickets(order, selected_items)
    await _mark_annual_card_refunded(db, order)
    if getattr(refund, "order_action", None) == "cancel_order":
        order.status = "cancelled"
        order.payment_status = "refunded"
    refund.completed_at = datetime.now(timezone.utc)
    if wechat_refund_id:
        refund.wechat_refund_id = wechat_refund_id
    await db.flush()
    return tx


def _is_refund_success_already_applied(refund: RefundRecord) -> bool:
    """退款记录已完成时，重放入口只补状态元数据，不再执行资金/库存副作用。"""
    return getattr(refund, "status", None) == "completed" or bool(getattr(refund, "completed_at", None))


def _apply_refund_record_to_order(
    order: Order,
    refund: RefundRecord,
    selected_items: Optional[list[Any]] = None,
) -> None:
    """退款真正生效后更新订单账面金额和订单项退款状态。"""
    existing_amount = Decimal(str(getattr(order, "refunded_amount", 0) or 0))
    refund_amount = Decimal(str(getattr(refund, "refund_amount", 0) or 0))
    target_amount = existing_amount + refund_amount
    actual_amount = Decimal(str(getattr(order, "actual_amount", 0) or 0))
    order.refunded_amount = min(target_amount, actual_amount)

    refund_items = list(getattr(refund, "items", []) or [])
    refund_item_ids = {item.order_item_id for item in refund_items}
    if selected_items is None:
        selected_items = [
            item
            for item in (getattr(order, "items", []) or [])
            if getattr(item, "id", None) in refund_item_ids
        ]
    for item in selected_items:
        item.refund_status = "refunded"


async def _validate_order_refundable(db: AsyncSession, order: Order) -> None:
    if getattr(order, "status", None) not in {"paid", "verified", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40940, "message": "订单状态不允许退款"},
        )
    if getattr(order, "refund_status", None) in {"pending", "processing", "refunded"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40943, "message": "订单已有退款处理中或已退款"},
        )
    if getattr(order, "order_type", None) == "annual_card":
        await _validate_annual_card_refund_window(db, order)


def _validate_refund_permission(
    *,
    refund_mode: str,
    order_action: str,
    requester_role: str,
) -> None:
    if refund_mode == "full" and order_action == "keep_order" and requester_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40341, "message": "全额退款且不取消订单仅超级管理员可操作"},
        )


def _select_refund_items(
    order: Order,
    *,
    refund_mode: str,
    items: Optional[list[dict[str, Any]]],
) -> list[Any]:
    order_items = list(getattr(order, "items", []) or [])
    if refund_mode in {"full", "partial"}:
        return order_items

    item_ids = {int(item["order_item_id"]) for item in (items or [])}
    selected = [item for item in order_items if item.id in item_ids]
    if len(selected) != len(item_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40042, "message": "退款明细包含不存在的订单项"},
        )
    return selected


def _calculate_system_amount(
    order: Order,
    *,
    refund_mode: str,
    selected_items: list[Any],
) -> Decimal:
    if refund_mode == "full":
        return _remaining_refundable_amount(order)
    return sum((Decimal(str(item.actual_price)) for item in selected_items), Decimal("0.00"))


def _remaining_refundable_amount(order: Order) -> Decimal:
    actual_amount = Decimal(str(getattr(order, "actual_amount", 0) or 0))
    refunded_amount = Decimal(str(getattr(order, "refunded_amount", 0) or 0))
    return actual_amount - refunded_amount


def _resolve_item_refund_amount(item: Any, items: Optional[list[dict[str, Any]]]) -> Decimal:
    if items:
        for item_data in items:
            if int(item_data["order_item_id"]) == item.id:
                return Decimal(str(item_data["refund_amount"]))
    return Decimal(str(item.actual_price))


def _resolve_item_refund_quantity(item: Any, items: Optional[list[dict[str, Any]]]) -> int:
    if items:
        for item_data in items:
            if int(item_data["order_item_id"]) == item.id:
                return int(item_data.get("quantity") or 1)
    return int(getattr(item, "quantity", 1) or 1)


def _resolve_risk_level(
    order: Order,
    refund_mode: str,
    order_action: str,
    refund_amount: Decimal,
) -> str:
    if order_action == "keep_order" and refund_mode == "full":
        return "high"
    if refund_amount != _remaining_refundable_amount(order):
        return "medium"
    return "normal"


def _void_tickets(order: Order, selected_items: Optional[list[Any]]) -> None:
    if selected_items is None:
        selected_item_ids = {item.id for item in (getattr(order, "items", []) or [])}
    else:
        selected_item_ids = {item.id for item in selected_items}
    for ticket in getattr(order, "tickets", []) or []:
        if getattr(ticket, "order_item_id", None) in selected_item_ids:
            ticket.verify_status = "refunded"


def _select_order_items_for_refund_record(order: Order, refund: RefundRecord) -> list[Any]:
    """按退款明细选出实际生效的订单项；兼容旧记录缺明细时全量处理。"""
    order_items = list(getattr(order, "items", []) or [])
    refund_items = list(getattr(refund, "items", []) or [])
    refund_item_ids = {item.order_item_id for item in refund_items}
    if refund_item_ids:
        return [
            item
            for item in order_items
            if getattr(item, "id", None) in refund_item_ids
        ]
    return order_items


async def _release_refund_record_inventory(
    db: AsyncSession,
    refund: RefundRecord,
    *,
    order: Optional[Order] = None,
    selected_items: Optional[list[Any]] = None,
) -> None:
    """按退款记录幂等释放库存，兼容旧库存和 v1.8 共享库存池。"""
    if not getattr(refund, "release_inventory", False):
        return
    if getattr(refund, "inventory_released", False):
        return

    if selected_items is None:
        if order is None:
            order = await _get_order_by_id(db, order_id=refund.order_id, site_id=refund.site_id)
        refund_items = list(getattr(refund, "items", []) or [])
        releasable_quantities = {
            item.order_item_id: getattr(item, "quantity", None)
            for item in refund_items
            if getattr(item, "release_inventory", True)
        }
        releasable_item_ids = set(releasable_quantities)
        if releasable_item_ids:
            selected_items = [
                item
                for item in (getattr(order, "items", []) or [])
                if getattr(item, "id", None) in releasable_item_ids
            ]
        else:
            selected_items = list(getattr(order, "items", []) or [])
    else:
        refund_items = list(getattr(refund, "items", []) or [])
        releasable_quantities = {
            item.order_item_id: getattr(item, "quantity", None)
            for item in refund_items
            if getattr(item, "release_inventory", True)
        }

    for item in selected_items:
        refund_quantity = releasable_quantities.get(getattr(item, "id", None))
        await order_service._refund_order_item_inventory(
            db,
            item,
            refund.order_id,
            quantity=refund_quantity,
        )

    refund.inventory_released = True


async def _get_order_by_id(
    db: AsyncSession,
    *,
    order_id: int,
    site_id: int,
) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.tickets))
        .where(
            Order.id == order_id,
            Order.site_id == site_id,
            Order.is_deleted.is_(False),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail={"code": 40401, "message": "订单不存在"})
    return order


async def _get_finance_account(db: AsyncSession, *, site_id: int) -> FinanceAccount:
    result = await db.execute(
        select(FinanceAccount).where(FinanceAccount.site_id == site_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail={"code": 40402, "message": "财务账户不存在"})
    return account


async def _find_existing_refund_tx(
    db: AsyncSession,
    *,
    refund_id: int,
    site_id: int,
) -> Optional[FinanceTransaction]:
    result = await db.execute(
        select(FinanceTransaction).where(
            FinanceTransaction.refund_record_id == refund_id,
            FinanceTransaction.site_id == site_id,
            FinanceTransaction.type == "refund",
            FinanceTransaction.is_deleted.is_(False),
        ).with_for_update()
    )
    return result.scalar_one_or_none()


def _resolve_refund_account_type(order: Order) -> str:
    if getattr(order, "order_type", None) == "annual_card":
        return "available"
    if getattr(order, "settlement_status", None) == "settled":
        return "available"
    return "pending"


async def _validate_annual_card_refund_window(db: AsyncSession, order: Order) -> None:
    membership_data = (getattr(order, "biz_data", None) or {}).get("membership_card") or {}
    refund_days = membership_data.get("refund_days")
    config_id = membership_data.get("config_id")
    if refund_days is None and config_id:
        result = await db.execute(
            select(AnnualCardConfig).where(
                AnnualCardConfig.id == int(config_id),
                AnnualCardConfig.site_id == order.site_id,
                AnnualCardConfig.is_deleted.is_(False),
            )
        )
        config = result.scalar_one_or_none()
        refund_days = getattr(config, "refund_days", None)
    refund_days = int(refund_days or 7)

    paid_at = getattr(order, "payment_time", None) or getattr(order, "created_at", None)
    if paid_at is None:
        return
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > paid_at + timedelta(days=refund_days):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40942, "message": f"年卡购买超过{refund_days}天，无法退款"},
        )


async def _mark_annual_card_refunded(db: AsyncSession, order: Order) -> None:
    if getattr(order, "order_type", None) != "annual_card":
        return
    result = await db.execute(
        select(AnnualCard).where(
            AnnualCard.order_id == order.id,
            AnnualCard.site_id == order.site_id,
            AnnualCard.is_deleted.is_(False),
        )
    )
    card = result.scalar_one_or_none()
    if card:
        card.status = "refunded"
