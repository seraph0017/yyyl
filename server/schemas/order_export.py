"""
v1.7 订单导出 Schema
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderExportCreateRequest(BaseModel):
    """创建订单导出任务请求"""

    model_config = ConfigDict(populate_by_name=True)

    filters: Dict[str, Any] = Field(default_factory=dict, description="订单筛选条件")
    file_format: str = Field(default="xlsx", description="文件格式")
    include_sensitive: bool = Field(default=False, description="是否包含敏感字段")

    @field_validator("file_format")
    @classmethod
    def validate_file_format(cls, value: str) -> str:
        if value not in {"xlsx", "csv"}:
            raise ValueError("file_format 必须为 xlsx 或 csv")
        return value


class OrderExportTaskResponse(BaseModel):
    """订单导出任务响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    site_id: int
    task_no: str
    filters: Dict[str, Any]
    file_format: str
    row_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_by: int
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
