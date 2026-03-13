"""
财务路由

- GET /overview — 财务概览
- POST /withdraw — 发起提现
- GET /transactions — 交易流水
- POST /deposits/{id}/refund — 退还押金
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from models.admin import AdminUser
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.finance import (
    DepositRecordResponse,
    DepositRefundRequest,
    FinanceAccountInfo,
    TransactionListParams,
    TransactionResponse,
    WithdrawRequest,
    WithdrawResponse,
)
from services import finance_service

router = APIRouter(prefix="/api/v1/admin/finance", tags=["财务"])


@router.get("/overview", summary="财务概览")
async def get_finance_overview(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取财务账户信息：各类余额、今日收入/退款等"""
    result = await finance_service.get_finance_overview(db)
    account_info = FinanceAccountInfo.model_validate(result)
    return ResponseModel.success(data=account_info)


@router.post("/withdraw", summary="发起提现")
async def withdraw(
    body: WithdrawRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """发起提现操作"""
    result = await finance_service.withdraw(
        db,
        amount=body.amount,
        operator_id=admin.id,
        bank_account=body.bank_account,
        remark=body.remark,
    )
    withdraw_resp = WithdrawResponse.model_validate(result)
    return ResponseModel.success(data=withdraw_resp, message="提现申请已提交")


@router.get("/transactions", summary="交易流水")
async def list_transactions(
    params: TransactionListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """查询交易流水列表，支持类型/账户/日期/订单筛选"""
    transactions, total = await finance_service.list_transactions(
        db,
        tx_type=params.type,
        account_type=params.account_type,
        date_start=params.date_start,
        date_end=params.date_end,
        order_id=params.order_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [TransactionResponse.model_validate(tx) for tx in transactions]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/deposits/{deposit_id}/refund", summary="退还押金")
async def refund_deposit(
    deposit_id: int,
    body: DepositRefundRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """退还押金：全额退还或部分退还（扣除损坏费用）"""
    deposit = await finance_service.return_deposit(
        db,
        deposit_id=deposit_id,
        return_amount=body.return_amount,
        operator_id=admin.id,
        remark=body.remark,
    )
    result = DepositRecordResponse.model_validate(deposit)
    return ResponseModel.success(data=result, message="押金退还完成")
