"""
资金结算服务

支付成功进入 pending 账户，订单完成后从 pending 结算到 available。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from models.finance import FinanceAccount, FinanceTransaction
from models.order import Order
from models.settlement import FinanceSettlement
from utils.helpers import generate_transaction_no


CASH_PAYMENT_METHODS = {"wechat_pay", "mock_pay"}
SETTLEMENT_PREFIX = "ST"


async def record_payment_pending_income(
    db: AsyncSession,
    order,
) -> Optional[FinanceTransaction]:
    """支付成功后将现金类订单金额计入 pending 账户，按订单幂等。"""
    if getattr(order, "payment_method", None) not in CASH_PAYMENT_METHODS:
        return None

    existing = await _find_existing_income_tx(db, order_id=order.id, site_id=order.site_id)
    if existing:
        return existing

    account = await _get_or_create_finance_account(db, site_id=order.site_id)
    amount = Decimal(str(order.actual_amount))
    account.pending_amount += amount
    account.total_income += amount

    tx = FinanceTransaction(
        transaction_no=generate_transaction_no("IN"),
        order_id=order.id,
        type="income",
        amount=amount,
        account_type="pending",
        from_account="wechat" if order.payment_method == "wechat_pay" else "mock_pay",
        to_account="pending",
        status="completed",
        remark="订单支付成功进入待结算账户",
        site_id=order.site_id,
    )
    db.add(tx)
    await db.flush()
    return tx


async def settle_completed_order(
    db: AsyncSession,
    order: Order,
    *,
    trigger_type: str = "auto",
) -> FinanceSettlement:
    """订单完成后将待结算金额转入可提现账户，按订单幂等。"""
    existing = await _find_completed_settlement(db, order_id=order.id, site_id=order.site_id)
    if existing:
        return existing

    account = await _get_or_create_finance_account(db, site_id=order.site_id)
    settlement = _apply_completed_order_settlement(
        db,
        order,
        account,
        trigger_type=trigger_type,
    )
    await db.flush()
    return settlement


def settle_completed_order_sync(
    db: Session,
    order: Order,
    *,
    trigger_type: str = "auto",
) -> FinanceSettlement:
    """同步会话版本，供 Celery worker 使用。"""
    existing = _find_completed_settlement_sync(db, order_id=order.id, site_id=order.site_id)
    if existing:
        return existing

    account = _get_or_create_finance_account_sync(db, site_id=order.site_id)
    settlement = _apply_completed_order_settlement(
        db,
        order,
        account,
        trigger_type=trigger_type,
    )
    db.flush()
    return settlement


async def list_settlements(
    db: AsyncSession,
    *,
    site_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[FinanceSettlement], int]:
    """查询结算记录列表。"""
    from sqlalchemy import func

    query = select(FinanceSettlement).where(
        FinanceSettlement.site_id == site_id,
        FinanceSettlement.is_deleted.is_(False),
    )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(FinanceSettlement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


def _apply_completed_order_settlement(
    db,
    order: Order,
    account: FinanceAccount,
    *,
    trigger_type: str,
) -> FinanceSettlement:
    amount = _calculate_settle_amount(order)
    if getattr(order, "status", None) != "completed" or amount <= 0:
        settlement = _build_failed_settlement(
            order,
            amount=max(amount, Decimal("0.00")),
            trigger_type=trigger_type,
            error_message="订单状态或可结算金额不满足结算条件",
        )
        order.settlement_status = "failed"
        db.add(settlement)
        return settlement

    if account.pending_amount < amount:
        settlement = _build_failed_settlement(
            order,
            amount=amount,
            trigger_type=trigger_type,
            error_message=f"待结算余额不足，当前: {account.pending_amount}",
        )
        order.settlement_status = "failed"
        db.add(settlement)
        return settlement

    account.pending_amount -= amount
    account.available_amount += amount
    order.settled_amount = Decimal(str(order.settled_amount or 0)) + amount
    order.settlement_status = "settled"

    settlement = FinanceSettlement(
        settlement_no=generate_transaction_no(SETTLEMENT_PREFIX),
        order_id=order.id,
        site_id=order.site_id,
        amount=amount,
        status="completed",
        trigger_type=trigger_type,
        settled_at=datetime.now(timezone.utc),
    )
    db.add(settlement)

    tx = FinanceTransaction(
        transaction_no=generate_transaction_no("SE"),
        order_id=order.id,
        type="settlement",
        amount=amount,
        account_type="available",
        from_account="pending",
        to_account="available",
        status="completed",
        remark=f"订单完成自动结算 order_id={order.id}",
        site_id=order.site_id,
    )
    db.add(tx)
    return settlement


async def _find_existing_income_tx(
    db: AsyncSession,
    *,
    order_id: int,
    site_id: int,
) -> Optional[FinanceTransaction]:
    result = await db.execute(
        select(FinanceTransaction).where(
            FinanceTransaction.order_id == order_id,
            FinanceTransaction.site_id == site_id,
            FinanceTransaction.type == "income",
            FinanceTransaction.account_type == "pending",
            FinanceTransaction.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def _find_completed_settlement(
    db: AsyncSession,
    *,
    order_id: int,
    site_id: int,
) -> Optional[FinanceSettlement]:
    result = await db.execute(
        select(FinanceSettlement).where(
            FinanceSettlement.order_id == order_id,
            FinanceSettlement.site_id == site_id,
            FinanceSettlement.status == "completed",
            FinanceSettlement.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


def _find_completed_settlement_sync(
    db: Session,
    *,
    order_id: int,
    site_id: int,
) -> Optional[FinanceSettlement]:
    return db.execute(
        select(FinanceSettlement).where(
            FinanceSettlement.order_id == order_id,
            FinanceSettlement.site_id == site_id,
            FinanceSettlement.status == "completed",
            FinanceSettlement.is_deleted.is_(False),
        )
    ).scalar_one_or_none()


async def _get_or_create_finance_account(
    db: AsyncSession,
    *,
    site_id: int,
) -> FinanceAccount:
    result = await db.execute(
        select(FinanceAccount).where(FinanceAccount.site_id == site_id)
    )
    account = result.scalar_one_or_none()
    if account:
        return account
    account = FinanceAccount(site_id=site_id)
    db.add(account)
    await db.flush()
    return account


def _get_or_create_finance_account_sync(db: Session, *, site_id: int) -> FinanceAccount:
    account = db.execute(
        select(FinanceAccount).where(FinanceAccount.site_id == site_id)
    ).scalar_one_or_none()
    if account:
        return account
    return _add_finance_account_sync(db, site_id=site_id)


def _add_finance_account_sync(db, *, site_id: int) -> FinanceAccount:
    account = FinanceAccount(site_id=site_id)
    db.add(account)
    db.flush()
    return account


def _calculate_settle_amount(order: Order) -> Decimal:
    actual_amount = Decimal(str(getattr(order, "actual_amount", 0) or 0))
    refunded_amount = Decimal(str(getattr(order, "refunded_amount", 0) or 0))
    settled_amount = Decimal(str(getattr(order, "settled_amount", 0) or 0))
    return actual_amount - refunded_amount - settled_amount


def _build_failed_settlement(
    order: Order,
    *,
    amount: Decimal,
    trigger_type: str,
    error_message: str,
) -> FinanceSettlement:
    return FinanceSettlement(
        settlement_no=generate_transaction_no(SETTLEMENT_PREFIX),
        order_id=order.id,
        site_id=order.site_id,
        amount=amount,
        status="failed",
        trigger_type=trigger_type,
        error_message=error_message,
    )
