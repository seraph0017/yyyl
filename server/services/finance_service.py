"""
财务服务

- get_finance_overview：财务概览
- list_transactions：交易流水
- withdraw：提现
- return_deposit：退还押金
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.finance import DepositRecord, FinanceAccount, FinanceTransaction
from utils.helpers import generate_transaction_no

logger = logging.getLogger(__name__)


async def get_finance_overview(
    db: AsyncSession,
    site_id: int = 1,
) -> Dict[str, Any]:
    """获取财务概览

    Args:
        db: 数据库会话
        site_id: 营地ID

    Returns:
        财务概览数据
    """
    result = await db.execute(
        select(FinanceAccount).where(FinanceAccount.site_id == site_id)
    )
    account = result.scalar_one_or_none()

    if account is None:
        return {
            "id": 0,
            "pending_amount": Decimal("0"),
            "available_amount": Decimal("0"),
            "deposit_amount": Decimal("0"),
            "maintenance_income": Decimal("0"),
            "total_income": Decimal("0"),
            "today_income": Decimal("0"),
            "today_refund": Decimal("0"),
            "month_income": Decimal("0"),
            "month_refund": Decimal("0"),
        }

    today = date.today()

    # 今日收入
    today_income_result = await db.execute(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.site_id == site_id,
            FinanceTransaction.type == "income",
            func.date(FinanceTransaction.created_at) == today,
        )
    )
    today_income = today_income_result.scalar() or Decimal("0")

    # 今日退款
    today_refund_result = await db.execute(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.site_id == site_id,
            FinanceTransaction.type == "refund",
            func.date(FinanceTransaction.created_at) == today,
        )
    )
    today_refund = today_refund_result.scalar() or Decimal("0")

    return {
        "id": account.id,
        "pending_amount": account.pending_amount,
        "available_amount": account.available_amount,
        "deposit_amount": account.deposit_amount,
        "maintenance_income": account.maintenance_income,
        "total_income": account.total_income,
        "today_income": today_income,
        "today_refund": today_refund,
        "month_income": Decimal("0"),  # TODO: 本月统计
        "month_refund": Decimal("0"),
    }


async def list_transactions(
    db: AsyncSession,
    *,
    site_id: int = 1,
    tx_type: Optional[str] = None,
    account_type: Optional[str] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    order_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[FinanceTransaction], int]:
    """交易流水查询

    Args:
        db: 数据库会话
        site_id: 营地ID
        tx_type: 交易类型
        account_type: 账户类型
        date_start: 开始日期
        date_end: 结束日期
        order_id: 关联订单ID
        page: 页码
        page_size: 每页数量

    Returns:
        (流水列表, 总数)
    """
    query = select(FinanceTransaction).where(
        FinanceTransaction.site_id == site_id,
        FinanceTransaction.is_deleted.is_(False),
    )

    if tx_type:
        query = query.where(FinanceTransaction.type == tx_type)
    if account_type:
        query = query.where(FinanceTransaction.account_type == account_type)
    if date_start:
        query = query.where(func.date(FinanceTransaction.created_at) >= date_start)
    if date_end:
        query = query.where(func.date(FinanceTransaction.created_at) <= date_end)
    if order_id:
        query = query.where(FinanceTransaction.order_id == order_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(FinanceTransaction.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    transactions = list(result.scalars().all())

    return transactions, total


async def withdraw(
    db: AsyncSession,
    amount: Decimal,
    operator_id: int,
    site_id: int = 1,
    bank_account: Optional[str] = None,
    remark: Optional[str] = None,
) -> Dict[str, Any]:
    """发起提现

    Args:
        db: 数据库会话
        amount: 提现金额
        operator_id: 操作人
        site_id: 营地ID
        bank_account: 银行账户
        remark: 备注

    Returns:
        提现结果
    """
    result = await db.execute(
        select(FinanceAccount).where(FinanceAccount.site_id == site_id)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "财务账户不存在"},
        )

    if account.available_amount < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40901, "message": f"可提现余额不足，当前: {account.available_amount}"},
        )

    # 扣减可提现金额
    account.available_amount -= amount

    # 创建交易流水
    tx = FinanceTransaction(
        transaction_no=generate_transaction_no("WD"),
        type="withdraw",
        amount=amount,
        account_type="available",
        from_account="available",
        to_account=bank_account or "bank",
        status="pending",
        remark=remark or "提现",
        operator_id=operator_id,
        site_id=site_id,
    )
    db.add(tx)
    await db.flush()

    logger.info(f"[财务] 提现: amount={amount}, operator={operator_id}")

    return {
        "transaction_no": tx.transaction_no,
        "amount": amount,
        "status": tx.status,
        "created_at": tx.created_at,
    }


async def return_deposit(
    db: AsyncSession,
    deposit_id: int,
    return_amount: Decimal,
    operator_id: int,
    remark: Optional[str] = None,
) -> DepositRecord:
    """退还押金

    Args:
        db: 数据库会话
        deposit_id: 押金记录ID
        return_amount: 退还金额
        operator_id: 操作人ID
        remark: 备注

    Returns:
        更新后的 DepositRecord
    """
    result = await db.execute(
        select(DepositRecord).where(
            DepositRecord.id == deposit_id,
            DepositRecord.is_deleted.is_(False),
        )
    )
    deposit = result.scalar_one_or_none()

    if deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40401, "message": "押金记录不存在"},
        )

    if deposit.status != "held":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40902, "message": "押金状态不允许退还"},
        )

    if return_amount > deposit.deposit_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40001, "message": "退还金额不能超过押金金额"},
        )

    deduct_amount = deposit.deposit_amount - return_amount

    if deduct_amount > 0:
        deposit.status = "partial_returned"
    else:
        deposit.status = "returned"

    deposit.return_amount = return_amount
    deposit.deduct_amount = deduct_amount
    deposit.processed_by = operator_id
    deposit.processed_at = datetime.now(timezone.utc)

    # TODO: 更新 FinanceAccount 的 deposit_amount

    await db.flush()
    logger.info(f"[财务] 押金退还: deposit_id={deposit_id}, return={return_amount}")
    return deposit
