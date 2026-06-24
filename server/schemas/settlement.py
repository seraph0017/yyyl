"""
v1.7 资金结算 Schema
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FinanceSettlementResponse(BaseModel):
    """结算记录响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    site_id: int
    order_id: int
    settlement_no: str
    amount: Decimal
    status: str
    trigger_type: str
    settled_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
