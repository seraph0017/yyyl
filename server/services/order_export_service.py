"""
订单导出服务

导出文件落在服务端私有目录，不挂载到 /images 等公开静态目录。
"""

from __future__ import annotations

import csv
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, status
from openpyxl import Workbook
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.admin import OperationLog
from models.export_task import OrderExportTask
from services import order_service


PRIVATE_EXPORT_DIR = Path(__file__).resolve().parents[1] / "private" / "exports" / "orders"
SYNC_EXPORT_LIMIT = 5000
EXPORT_EXPIRE_DAYS = 7


async def create_order_export_task(
    db: AsyncSession,
    *,
    site_id: int,
    filters: dict[str, Any],
    file_format: str,
    include_sensitive: bool,
    created_by: int,
) -> OrderExportTask:
    """创建订单导出任务；5000 行以内同步完成。"""
    task = OrderExportTask(
        site_id=site_id,
        task_no=_generate_task_no(),
        filters={**filters, "include_sensitive": include_sensitive},
        file_format=file_format,
        status="pending",
        created_by=created_by,
        expires_at=datetime.now(timezone.utc) + timedelta(days=EXPORT_EXPIRE_DAYS),
    )
    db.add(task)
    await db.flush()

    orders, total = await _list_orders_for_export(db, site_id=site_id, filters=filters)
    if total > SYNC_EXPORT_LIMIT:
        task.status = "pending"
        task.row_count = total
        await db.flush()
        return task

    task.status = "processing"
    await db.flush()
    try:
        task.file_path = _write_export_file(
            site_id=site_id,
            task_no=task.task_no,
            file_format=file_format,
            orders=orders,
            include_sensitive=include_sensitive,
        )
        task.row_count = total
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        _add_export_operation_log(
            db,
            site_id=site_id,
            operator_id=created_by,
            task=task,
            filters=filters,
        )
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)[:500]
    await db.flush()
    return task


async def list_export_tasks(
    db: AsyncSession,
    *,
    site_id: int,
    page: int,
    page_size: int,
) -> tuple[list[OrderExportTask], int]:
    query = select(OrderExportTask).where(
        OrderExportTask.site_id == site_id,
        OrderExportTask.is_deleted.is_(False),
    )
    count_result = await db.execute(
        select(OrderExportTask.id).where(
            OrderExportTask.site_id == site_id,
            OrderExportTask.is_deleted.is_(False),
        )
    )
    total = len(count_result.scalars().all())
    result = await db.execute(
        query.order_by(OrderExportTask.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_export_task(
    db: AsyncSession,
    *,
    site_id: int,
    task_id: int,
) -> Optional[OrderExportTask]:
    result = await db.execute(
        select(OrderExportTask).where(
            OrderExportTask.id == task_id,
            OrderExportTask.site_id == site_id,
            OrderExportTask.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def get_export_download_path(
    db: AsyncSession,
    *,
    site_id: int,
    task_id: int,
) -> Path:
    task = await get_export_task(db, site_id=site_id, task_id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_EXPORT_NOT_FOUND", "message": "导出任务不存在"},
        )
    if task.status != "completed" or not task.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ORDER_EXPORT_NOT_READY", "message": "导出文件尚未生成"},
        )
    if task.expires_at and task.expires_at < datetime.now(timezone.utc):
        task.status = "expired"
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "ORDER_EXPORT_EXPIRED", "message": "导出文件已过期"},
        )
    file_path = Path(task.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_EXPORT_FILE_NOT_FOUND", "message": "导出文件不存在"},
        )
    return file_path


async def _list_orders_for_export(
    db: AsyncSession,
    *,
    site_id: int,
    filters: dict[str, Any],
) -> tuple[list[Any], int]:
    allowed = {
        "user_id",
        "status",
        "order_type",
        "date_start",
        "date_end",
        "keyword",
        "payment_status",
        "product_id",
        "product_type",
        "booking_date_start",
        "booking_date_end",
        "payment_time_start",
        "payment_time_end",
        "amount_min",
        "amount_max",
        "verify_status",
        "source_channel",
    }
    clean_filters = {key: value for key, value in filters.items() if key in allowed and value not in ("", None)}
    return await order_service.list_orders(
        db,
        site_id=site_id,
        user_id=clean_filters.get("user_id"),
        order_status=clean_filters.get("status"),
        order_type=clean_filters.get("order_type"),
        date_start=clean_filters.get("date_start"),
        date_end=clean_filters.get("date_end"),
        keyword=clean_filters.get("keyword"),
        payment_status=clean_filters.get("payment_status"),
        product_id=clean_filters.get("product_id"),
        product_type=clean_filters.get("product_type"),
        booking_date_start=clean_filters.get("booking_date_start"),
        booking_date_end=clean_filters.get("booking_date_end"),
        payment_time_start=clean_filters.get("payment_time_start"),
        payment_time_end=clean_filters.get("payment_time_end"),
        amount_min=clean_filters.get("amount_min"),
        amount_max=clean_filters.get("amount_max"),
        verify_status=clean_filters.get("verify_status"),
        source_channel=clean_filters.get("source_channel"),
        page=1,
        page_size=SYNC_EXPORT_LIMIT,
    )


def _write_export_file(
    *,
    site_id: int,
    task_no: str,
    file_format: str,
    orders: list[Any],
    include_sensitive: bool,
) -> str:
    export_dir = PRIVATE_EXPORT_DIR / str(site_id)
    export_dir.mkdir(parents=True, exist_ok=True)
    headers = ["订单号", "状态", "支付状态", "实付金额", "来源渠道", "下单时间", "商品"]
    if include_sensitive:
        headers.insert(1, "用户昵称")
        headers.insert(2, "手机号")
    if file_format == "csv":
        file_path = export_dir / f"{task_no}.csv"
        with file_path.open("w", newline="", encoding="utf-8-sig") as fp:
            writer = csv.writer(fp)
            writer.writerow(headers)
            for order in orders:
                writer.writerow(_build_export_row(order, include_sensitive=include_sensitive))
        return str(file_path)

    file_path = export_dir / f"{task_no}.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "订单导出"
    worksheet.append(headers)
    for order in orders:
        worksheet.append(_build_export_row(order, include_sensitive=include_sensitive))
    workbook.save(file_path)
    return str(file_path)


def _build_export_row(order: Any, *, include_sensitive: bool) -> list[Any]:
    products = "；".join(
        [
            getattr(item, "product_name", "") or str(getattr(item, "product_id", ""))
            for item in getattr(order, "items", [])
        ]
    )
    row = [
        getattr(order, "order_no", ""),
        getattr(order, "status", ""),
        getattr(order, "payment_status", ""),
        getattr(order, "actual_amount", ""),
        getattr(order, "source_channel", "") or "",
        getattr(order, "created_at", ""),
        products,
    ]
    if include_sensitive:
        user = getattr(order, "user", None)
        row.insert(1, getattr(user, "nickname", "") or "")
        row.insert(2, getattr(user, "phone", "") or "")
    return row


def _add_export_operation_log(
    db: AsyncSession,
    *,
    site_id: int,
    operator_id: int,
    task: OrderExportTask,
    filters: dict[str, Any],
) -> None:
    db.add(
        OperationLog(
            operator_id=operator_id,
            operator_name="system",
            action="order_export",
            target_type="order_export_task",
            target_id=task.id,
            detail={
                "task_no": task.task_no,
                "filters": filters,
                "row_count": task.row_count,
                "file_format": task.file_format,
            },
            site_id=site_id,
        )
    )


def _generate_task_no() -> str:
    return "EXP" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + secrets.token_hex(3).upper()
