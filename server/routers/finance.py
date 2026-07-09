"""
财务路由

- GET /overview — 财务概览
- POST /withdraw — 发起提现
- GET /transactions — 交易流水
- POST /deposits/{id}/refund — 退还押金
"""

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_admin
from middleware.site import get_site_id
from models.admin import AdminUser
from schemas.common import PaginatedResponse, PaginationParams, ResponseModel
from schemas.settlement import FinanceSettlementResponse
from schemas.finance import (
    DepositRecordResponse,
    DepositRefundRequest,
    FinanceAccountInfo,
    TransactionListParams,
    TransactionResponse,
    WithdrawRequest,
    WithdrawResponse,
)
from services import finance_service, settlement_service
from utils.security import verify_token

router = APIRouter(prefix="/api/v1/admin/finance", tags=["财务"])


def _get_admin_role_code(admin: AdminUser) -> str:
    return getattr(getattr(admin, "role", None), "role_code", "") or ""


def _get_required_confirm_site_id(request: Request) -> int:
    raw_site_id = request.headers.get("X-Site-Id") or request.headers.get("x-site-id")
    if raw_site_id is None or str(raw_site_id).strip() == "":
        raise HTTPException(status_code=400, detail={"code": 40012, "message": "高风险财务操作必须显式传入 X-Site-Id"})
    try:
        site_id = int(raw_site_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": 40012, "message": "X-Site-Id 必须为有效营地ID"}) from exc
    if site_id not in (1, 2):
        raise HTTPException(status_code=400, detail={"code": 40012, "message": "X-Site-Id 必须为有效营地ID"})
    return site_id


def _stable_request_hash(payload: Any) -> str:
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _request_json_payload(request: Request, fallback: Any) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = fallback.model_dump(mode="json", exclude_none=True)
    if not isinstance(payload, dict):
        payload = {}
    return {key: value for key, value in payload.items() if value is not None}


def _require_confirm_token(
    *,
    admin: AdminUser,
    site_id: int,
    action: str,
    payload: Any,
    confirm_token: str | None,
) -> None:
    if _get_admin_role_code(admin) != "super_admin":
        raise HTTPException(status_code=403, detail={"code": 40302, "message": "仅超级管理员可执行该高风险财务操作"})
    if not confirm_token:
        raise HTTPException(status_code=403, detail={"code": 40321, "message": "缺少高风险财务操作确认"})
    try:
        token_data = verify_token(confirm_token)
    except JWTError as exc:
        raise HTTPException(status_code=403, detail={"code": 40322, "message": "高风险确认已失效，请重新确认"}) from exc
    expected_sub = f"admin:{admin.id}"
    if token_data.get("token_type") != "access" or token_data.get("confirm_type") != "operation":
        raise HTTPException(status_code=403, detail={"code": 40322, "message": "高风险确认已失效，请重新确认"})
    if token_data.get("sub") != expected_sub or token_data.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail={"code": 40323, "message": "高风险确认用户不匹配"})
    if int(token_data.get("site_id") or 0) != int(site_id):
        raise HTTPException(status_code=403, detail={"code": 40324, "message": "高风险确认营地不匹配"})
    if token_data.get("action") != action:
        raise HTTPException(status_code=403, detail={"code": 40325, "message": "高风险确认操作不匹配"})
    if token_data.get("request_hash") != _stable_request_hash(payload):
        raise HTTPException(status_code=403, detail={"code": 40326, "message": "高风险确认内容不匹配，请重新确认"})


@router.get("/overview", summary="财务概览")
async def get_finance_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取财务账户信息：各类余额、今日收入/退款等"""
    site_id = get_site_id(request)
    result = await finance_service.get_finance_overview(db, site_id=site_id)
    account_info = FinanceAccountInfo.model_validate(result)
    return ResponseModel.success(data=account_info)


@router.post("/withdraw", summary="发起提现")
async def withdraw(
    body: WithdrawRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    x_confirm_token: str | None = Header(default=None, alias="X-Confirm-Token"),
):
    """发起提现操作"""
    site_id = _get_required_confirm_site_id(request)
    payload = await _request_json_payload(request, body)
    _require_confirm_token(
        admin=admin,
        site_id=site_id,
        action="finance:withdraw",
        payload=payload,
        confirm_token=x_confirm_token,
    )
    result = await finance_service.withdraw(
        db,
        amount=body.amount,
        operator_id=admin.id,
        site_id=site_id,
        bank_account=body.bank_account,
        remark=body.remark,
    )
    withdraw_resp = WithdrawResponse.model_validate(result)
    return ResponseModel.success(data=withdraw_resp, message="提现申请已提交")


@router.get("/transactions", summary="交易流水")
async def list_transactions(
    request: Request,
    params: TransactionListParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """查询交易流水列表，支持类型/账户/日期/订单筛选"""
    site_id = get_site_id(request)
    transactions, total = await finance_service.list_transactions(
        db,
        site_id=site_id,
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


@router.get("/settlements", summary="结算记录列表")
async def list_settlements(
    request: Request,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """查询订单资金结算记录。"""
    site_id = get_site_id(request)
    settlements, total = await settlement_service.list_settlements(
        db,
        site_id=site_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return PaginatedResponse.create(
        items=[FinanceSettlementResponse.model_validate(item) for item in settlements],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/deposits/{deposit_id}/refund", summary="退还押金")
async def refund_deposit(
    deposit_id: int,
    body: DepositRefundRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    x_confirm_token: str | None = Header(default=None, alias="X-Confirm-Token"),
):
    """退还押金：全额退还或部分退还（扣除损坏费用）"""
    site_id = _get_required_confirm_site_id(request)
    payload = {"deposit_id": deposit_id, **await _request_json_payload(request, body)}
    _require_confirm_token(
        admin=admin,
        site_id=site_id,
        action="finance:deposit_refund",
        payload=payload,
        confirm_token=x_confirm_token,
    )
    deposit = await finance_service.return_deposit(
        db,
        deposit_id=deposit_id,
        return_amount=body.return_amount,
        operator_id=admin.id,
        site_id=site_id,
        remark=body.remark,
    )
    result = DepositRecordResponse.model_validate(deposit)
    return ResponseModel.success(data=result, message="押金退还完成")
