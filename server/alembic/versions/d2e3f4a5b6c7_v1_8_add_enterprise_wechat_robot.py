"""v1.8 add enterprise wechat robot

Revision ID: d2e3f4a5b6c7
Revises: c9d8e7f6a5b4
Create Date: 2026-06-26 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return table_name in set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _table_exists("enterprise_wechat_robot_config"):
        op.create_table(
            "enterprise_wechat_robot_config",
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("name", sa.String(length=128), nullable=False, comment="机器人名称"),
            sa.Column("webhook_url_ciphertext", sa.Text(), nullable=False, comment="企业微信群机器人 webhook 密文，禁止明文入库"),
            sa.Column("secret_ciphertext", sa.Text(), nullable=True, comment="机器人 secret 密文，禁止明文入库"),
            sa.Column("status", sa.String(length=20), server_default="active", nullable=False, comment="状态"),
            sa.Column("created_by", sa.BigInteger(), nullable=True, comment="创建管理员ID"),
            sa.Column("updated_by", sa.BigInteger(), nullable=True, comment="最近更新管理员ID"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.PrimaryKeyConstraint("id"),
            comment="v1.8 企业微信群机器人配置",
        )
        op.create_index("idx_ew_robot_site_status", "enterprise_wechat_robot_config", ["site_id", "status"])

    if not _table_exists("enterprise_wechat_robot_message_log"):
        op.create_table(
            "enterprise_wechat_robot_message_log",
            sa.Column("robot_config_id", sa.BigInteger(), nullable=False, comment="机器人配置ID"),
            sa.Column("site_id", sa.BigInteger(), server_default="1", nullable=False, comment="营地ID"),
            sa.Column("message_type", sa.String(length=30), server_default="text", nullable=False, comment="消息类型"),
            sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False, comment="发送请求体"),
            sa.Column("response_code", sa.Integer(), nullable=True, comment="企业微信返回 errcode 或 HTTP 状态码"),
            sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="企业微信返回体"),
            sa.Column("send_status", sa.String(length=20), nullable=False, comment="发送状态"),
            sa.Column("error_message", sa.String(length=512), nullable=True, comment="失败原因"),
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记"),
            sa.ForeignKeyConstraint(["robot_config_id"], ["enterprise_wechat_robot_config.id"]),
            sa.PrimaryKeyConstraint("id"),
            comment="v1.8 企业微信群机器人消息发送日志",
        )
        op.create_index("idx_ew_robot_log_config", "enterprise_wechat_robot_message_log", ["robot_config_id"])
        op.create_index("idx_ew_robot_log_site_status", "enterprise_wechat_robot_message_log", ["site_id", "send_status"])


def downgrade() -> None:
    if _table_exists("enterprise_wechat_robot_message_log"):
        op.drop_index("idx_ew_robot_log_site_status", table_name="enterprise_wechat_robot_message_log", if_exists=True)
        op.drop_index("idx_ew_robot_log_config", table_name="enterprise_wechat_robot_message_log", if_exists=True)
        op.drop_table("enterprise_wechat_robot_message_log")

    if _table_exists("enterprise_wechat_robot_config"):
        op.drop_index("idx_ew_robot_site_status", table_name="enterprise_wechat_robot_config", if_exists=True)
        op.drop_table("enterprise_wechat_robot_config")
