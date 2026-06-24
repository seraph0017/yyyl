"""
v1.7 统一退款服务
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.finance import FinanceAccount, FinanceTransaction
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
    _validate_order_refundable(order)
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
            quantity=getattr(item, "quantity", 1) or 1,
            release_inventory=release_inventory,
        )
        db.add(refund_item)
        item.refund_status = "refunded"

        if order_action == "cancel_order" and release_inventory and getattr(item, "date", None):
            await order_service._refund_inventory(
                db,
                item.product_id,
                item.date,
                item.quantity,
                order.id,
                item.sku_id,
                item.time_slot,
            )

    order.refunded_amount = Decimal(str(getattr(order, "refunded_amount", 0) or 0)) + refund_amount

    if order_action == "cancel_order":
        order.status = "cancelled"
        order.payment_status = "refunded"
        _void_tickets(order, selected_items)

    await db.flush()
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
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RefundRecord], int]:
    query = select(RefundRecord).where(
        RefundRecord.site_id == site_id,
        RefundRecord.is_deleted.is_(False),
    )
    if order_id:
        query = query.where(RefundRecord.order_id == order_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(
        query.order_by(RefundRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


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
        )
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

    await db.flush()
    return refund


async def apply_refund_success(
    db: AsyncSession,
    refund: RefundRecord,
    *,
    wechat_refund_id: Optional[str] = None,
) -> Optional[FinanceTransaction]:
    """退款成功后扣减财务账户并写退款流水，按退款记录幂等。"""
    existing = await _find_existing_refund_tx(db, refund_id=refund.id, site_id=refund.site_id)
    if existing:
        refund.status = "completed"
        refund.completed_at = refund.completed_at or datetime.now(timezone.utc)
        if wechat_refund_id:
            refund.wechat_refund_id = wechat_refund_id
        await db.flush()
        return existing

    order = await _get_order_by_id(db, order_id=refund.order_id, site_id=refund.site_id)
    account = await _get_finance_account(db, site_id=refund.site_id)
    amount = Decimal(str(refund.refund_amount))
    account_type = _resolve_refund_account_type(order)

    if account_type == "available":
        if account.available_amount < amount:
            refund.status = "failed"
            order.refund_status = "rejected"
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40942, "message": f"可提现余额不足，当前: {account.available_amount}"},
            )
        account.available_amount -= amount
    else:
        if account.pending_amount < amount:
            refund.status = "failed"
            order.refund_status = "rejected"
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 40943, "message": f"待结算余额不足，当前: {account.pending_amount}"},
            )
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
    refund.status = "completed"
    order.refund_status = "refunded"
    refund.completed_at = datetime.now(timezone.utc)
    if wechat_refund_id:
        refund.wechat_refund_id = wechat_refund_id
    await db.flush()
    return tx


def _validate_order_refundable(order: Order) -> None:
    if getattr(order, "status", None) not in {"paid", "verified", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40940, "message": "订单状态不允许退款"},
        )


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


def _void_tickets(order: Order, selected_items: list[Any]) -> None:
    selected_item_ids = {item.id for item in selected_items}
    for ticket in getattr(order, "tickets", []) or []:
        if getattr(ticket, "order_item_id", None) in selected_item_ids:
            ticket.verify_status = "refunded"


async def _get_order_by_id(
    db: AsyncSession,
    *,
    order_id: int,
    site_id: int,
) -> Order:
    result = await db.execute(
        select(Order).where(
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
        )
    )
    return result.scalar_one_or_none()


def _resolve_refund_account_type(order: Order) -> str:
    if getattr(order, "settlement_status", None) == "settled":
        return "available"
    return "pending"
