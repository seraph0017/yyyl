"""v1.7 add qrcode refund settlement export

Revision ID: b7e2f8a9c1d4
Revises: 5d456f22d64b
Create Date: 2026-06-18 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7e2f8a9c1d4"
down_revision: Union[str, None] = "5d456f22d64b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return table_name in set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    # ---- order 扩展字段 ----
    _add_column_if_missing("order", sa.Column("source_qrcode_id", sa.BigInteger(), nullable=True, comment="来源小程序码ID"))
    _add_column_if_missing("order", sa.Column("source_channel", sa.String(length=64), nullable=True, comment="来源渠道"))
    _add_column_if_missing("order", sa.Column("source_scanned_at", sa.DateTime(timezone=True), nullable=True, comment="来源扫码时间"))
    _add_column_if_missing("order", sa.Column("settled_amount", sa.Numeric(10, 2), server_default="0", nullable=False, comment="累计已结算金额"))
    _add_column_if_missing("order", sa.Column("settlement_status", sa.String(length=20), server_default="unsettled", nullable=False, comment="结算状态"))
    _add_column_if_missing("order", sa.Column("refund_status", sa.String(length=20), server_default="none", nullable=False, comment="退款状态"))

    _add_column_if_missing("finance_transaction", sa.Column("refund_record_id", sa.BigInteger(), nullable=True, comment="关联退款记录ID"))

    # ---- 账户非负约束 ----
    try:
        op.create_check_constraint(
            "ck_finance_pending_non_negative",
            "finance_account",
            "pending_amount >= 0",
        )
    except Exception:
        pass
    try:
        op.create_check_constraint(
            "ck_finance_available_non_negative",
            "finance_account",
            "available_amount >= 0",
        )
    except Exception:
        pass

    # ---- 小程序码表 ----
    if not _table_exists("mini_program_qrcode"):
        op.create_table(
            "mini_program_qrcode",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("target_type", sa.String(length=32), nullable=False, comment="目标类型"),
            sa.Column("target_key", sa.String(length=128), nullable=False, comment="目标ID或页面标识"),
            sa.Column("title", sa.String(length=128), nullable=False, comment="二维码标题"),
            sa.Column("path", sa.String(length=256), nullable=False, comment="小程序内部跳转路径"),
            sa.Column("scene", sa.String(length=128), nullable=False, comment="微信 scene 参数"),
            sa.Column("short_code", sa.String(length=32), nullable=False, comment="短码"),
            sa.Column("channel", sa.String(length=64), server_default="default", nullable=False, comment="渠道"),
            sa.Column("image_url", sa.String(length=512), nullable=True, comment="二维码图片URL"),
            sa.Column("status", sa.String(length=16), server_default="active", nullable=False, comment="状态"),
            sa.Column("generated_by", sa.BigInteger(), nullable=True, comment="生成管理员ID"),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True, comment="生成时间"),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True, comment="最近扫码时间"),
            sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False, comment="扫码次数"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("short_code"),
            comment="小程序码主表",
        )
        op.create_index("idx_qrcode_short_code", "mini_program_qrcode", ["short_code"], unique=True)
        op.create_index("idx_qrcode_site_status", "mini_program_qrcode", ["site_id", "status"], unique=False)
        op.create_index(
            "uq_qrcode_site_target_channel_scene",
            "mini_program_qrcode",
            ["site_id", "target_type", "target_key", "channel", "scene"],
            unique=True,
            postgresql_where=sa.text("is_deleted = false"),
        )

    if not _table_exists("mini_program_qrcode_scan_log"):
        op.create_table(
            "mini_program_qrcode_scan_log",
            sa.Column("site_id", sa.BigInteger(), nullable=False, comment="营地ID"),
            sa.Column("qr_code_id", sa.BigInteger(), nullable=False, comment="二维码ID"),
            sa.Column("user_id", sa.BigInteger(), nullable=True, comment="用户ID"),
            sa.Column("openid", sa.String(length=64), nullable=True, comment="微信 openid"),
            sa.Column("channel", sa.String(length=64), nullable=True, comment="渠道"),
            sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False, comment="扫码时间"),
            sa.Column("raw_scene", sa.String(length=256), nullable=True, comment="原始 scene"),
            sa.Column("client_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="客户端信息"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.ForeignKeyConstraint(["qr_code_id"], ["mini_program_qrcode.id"]),
            sa.PrimaryKeyConstraint("id"),
            comment="小程序码扫码日志",
        )
        op.create_index("idx_qrcode_scan_qr_time", "mini_program_qrcode_scan_log", ["qr_code_id", "scanned_at"], unique=False)
        op.create_index("idx_qrcode_scan_site_time", "mini_program_qrcode_scan_log", ["site_id", "scanned_at"], unique=False)

    # ---- 退款表 ----
    if not _table_exists("refund_record"):
        op.create_table(
            "refund_record",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("order_id", sa.BigInteger(), nullable=False, comment="订单ID"),
            sa.Column("refund_no", sa.String(length=40), nullable=False, unique=True, comment="退款单号"),
            sa.Column("refund_mode", sa.String(length=20), nullable=False, comment="退款模式"),
            sa.Column("order_action", sa.String(length=20), nullable=False, comment="订单处理"),
            sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False, comment="实际退款金额"),
            sa.Column("system_amount", sa.Numeric(10, 2), nullable=False, comment="系统计算金额"),
            sa.Column("release_inventory", sa.Boolean(), server_default="true", nullable=False, comment="是否释放库存"),
            sa.Column("reason", sa.String(length=500), nullable=False, comment="退款原因"),
            sa.Column("risk_level", sa.String(length=20), server_default="normal", nullable=False, comment="风险等级"),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False, comment="状态"),
            sa.Column("wechat_refund_id", sa.String(length=64), nullable=True, comment="微信退款ID"),
            sa.Column("requested_by", sa.BigInteger(), nullable=False, comment="申请人"),
            sa.Column("approved_by", sa.BigInteger(), nullable=True, comment="审批人"),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True, comment="审批时间"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.PrimaryKeyConstraint("id"),
            comment="退款主记录",
        )
        op.create_index("idx_refund_site_status", "refund_record", ["site_id", "status"], unique=False)
        op.create_index("idx_refund_order", "refund_record", ["order_id"], unique=False)
        op.create_index("idx_refund_no", "refund_record", ["refund_no"], unique=True)

    if not _table_exists("refund_record_item"):
        op.create_table(
            "refund_record_item",
            sa.Column("refund_record_id", sa.BigInteger(), nullable=False, comment="退款记录ID"),
            sa.Column("order_item_id", sa.BigInteger(), nullable=False, comment="订单项ID"),
            sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False, comment="退款金额"),
            sa.Column("quantity", sa.Integer(), server_default="1", nullable=False, comment="数量"),
            sa.Column("release_inventory", sa.Boolean(), server_default="true", nullable=False, comment="是否释放库存"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.ForeignKeyConstraint(["refund_record_id"], ["refund_record.id"]),
            sa.PrimaryKeyConstraint("id"),
            comment="退款订单项明细",
        )
        op.create_index("idx_refund_item_record", "refund_record_item", ["refund_record_id"], unique=False)
        op.create_index("idx_refund_item_order_item", "refund_record_item", ["order_item_id"], unique=False)

    # ---- 结算表 ----
    if not _table_exists("finance_settlement"):
        op.create_table(
            "finance_settlement",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("order_id", sa.BigInteger(), nullable=False, comment="订单ID"),
            sa.Column("settlement_no", sa.String(length=40), nullable=False, comment="结算单号"),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False, comment="结算金额"),
            sa.Column("status", sa.String(length=20), server_default="completed", nullable=False, comment="状态"),
            sa.Column("trigger_type", sa.String(length=32), nullable=False, comment="触发方式"),
            sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True, comment="结算时间"),
            sa.Column("error_message", sa.String(length=500), nullable=True, comment="失败原因"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("order_id", "settlement_no", name="uq_settlement_order_no"),
            comment="订单资金结算记录",
        )
        op.create_index("idx_settlement_site_status", "finance_settlement", ["site_id", "status"], unique=False)
        op.create_index("idx_settlement_order", "finance_settlement", ["order_id"], unique=False)

    # ---- 订单导出任务 ----
    if not _table_exists("order_export_task"):
        op.create_table(
            "order_export_task",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("task_no", sa.String(length=40), nullable=False, unique=True, comment="任务号"),
            sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="筛选条件"),
            sa.Column("file_format", sa.String(length=10), server_default="xlsx", nullable=False, comment="文件格式"),
            sa.Column("file_path", sa.String(length=512), nullable=True, comment="私有文件路径"),
            sa.Column("row_count", sa.Integer(), nullable=True, comment="导出行数"),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False, comment="状态"),
            sa.Column("error_message", sa.String(length=500), nullable=True, comment="错误信息"),
            sa.Column("created_by", sa.BigInteger(), nullable=False, comment="创建人"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, comment="过期时间"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.PrimaryKeyConstraint("id"),
            comment="订单导出任务",
        )
        op.create_index("idx_order_export_site_status", "order_export_task", ["site_id", "status"], unique=False)
        op.create_index("idx_order_export_creator", "order_export_task", ["created_by"], unique=False)


def downgrade() -> None:
    for index_name, table_name in [
        ("idx_order_export_creator", "order_export_task"),
        ("idx_order_export_site_status", "order_export_task"),
    ]:
        if _table_exists(table_name):
            op.drop_index(index_name, table_name=table_name)
    if _table_exists("order_export_task"):
        op.drop_table("order_export_task")

    for index_name in ["idx_settlement_order", "idx_settlement_site_status"]:
        if _table_exists("finance_settlement"):
            op.drop_index(index_name, table_name="finance_settlement")
    if _table_exists("finance_settlement"):
        op.drop_table("finance_settlement")

    for index_name in ["idx_refund_item_order_item", "idx_refund_item_record"]:
        if _table_exists("refund_record_item"):
            op.drop_index(index_name, table_name="refund_record_item")
    if _table_exists("refund_record_item"):
        op.drop_table("refund_record_item")

    for index_name in ["idx_refund_no", "idx_refund_order", "idx_refund_site_status"]:
        if _table_exists("refund_record"):
            op.drop_index(index_name, table_name="refund_record")
    if _table_exists("refund_record"):
        op.drop_table("refund_record")

    for index_name in ["idx_qrcode_scan_site_time", "idx_qrcode_scan_qr_time"]:
        if _table_exists("mini_program_qrcode_scan_log"):
            op.drop_index(index_name, table_name="mini_program_qrcode_scan_log")
    if _table_exists("mini_program_qrcode_scan_log"):
        op.drop_table("mini_program_qrcode_scan_log")

    for index_name in ["uq_qrcode_site_target_channel_scene", "idx_qrcode_site_status", "idx_qrcode_short_code"]:
        if _table_exists("mini_program_qrcode"):
            op.drop_index(index_name, table_name="mini_program_qrcode")
    if _table_exists("mini_program_qrcode"):
        op.drop_table("mini_program_qrcode")

    for constraint_name in ["ck_finance_available_non_negative", "ck_finance_pending_non_negative"]:
        try:
            op.drop_constraint(constraint_name, "finance_account", type_="check")
        except Exception:
            pass

    if "refund_record_id" in _columns("finance_transaction"):
        op.drop_column("finance_transaction", "refund_record_id")

    for column_name in [
        "refund_status",
        "settlement_status",
        "settled_amount",
        "source_scanned_at",
        "source_channel",
        "source_qrcode_id",
    ]:
        if column_name in _columns("order"):
            op.drop_column("order", column_name)
