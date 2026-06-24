"""
导出任务模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class OrderExportTask(Base):
    """订单导出任务"""

    __tablename__ = "order_export_task"
    __table_args__ = (
        Index("idx_order_export_site_status", "site_id", "status"),
        Index("idx_order_export_creator", "created_by"),
        {"comment": "订单导出任务"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    task_no: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True, comment="任务号"
    )
    filters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="筛选条件"
    )
    file_format: Mapped[str] = mapped_column(
        String(10), nullable=False, default="xlsx", server_default="xlsx",
        comment="文件格式"
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="私有文件路径"
    )
    row_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="导出行数"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending",
        comment="状态: pending/processing/completed/failed/expired"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="错误信息"
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="创建人"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="过期时间"
    )
