"""
v1.8 企业微信群机器人模型

仅支持企业微信群机器人/企业微信应用消息能力，不接入个人微信群自动化。
"""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class EnterpriseWechatRobotStatus(str, enum.Enum):
    """企业微信群机器人配置状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class EnterpriseWechatRobotSendStatus(str, enum.Enum):
    """企业微信群机器人消息发送状态"""

    SUCCESS = "success"
    FAILED = "failed"


class EnterpriseWechatRobotConfig(Base):
    """企业微信群机器人配置"""

    __tablename__ = "enterprise_wechat_robot_config"
    __table_args__ = (
        Index("idx_ew_robot_site_status", "site_id", "status"),
        {"comment": "v1.8 企业微信群机器人配置"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="机器人名称"
    )
    webhook_url_ciphertext: Mapped[str] = mapped_column(
        Text, nullable=False, comment="企业微信群机器人 webhook 密文，禁止明文入库"
    )
    secret_ciphertext: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="机器人 secret 密文，禁止明文入库"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EnterpriseWechatRobotStatus.ACTIVE.value,
        server_default=EnterpriseWechatRobotStatus.ACTIVE.value,
        comment="状态: active/inactive",
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="创建管理员ID"
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="最近更新管理员ID"
    )

    message_logs: Mapped[list["EnterpriseWechatRobotMessageLog"]] = relationship(
        back_populates="robot_config",
        lazy="noload",
    )


class EnterpriseWechatRobotMessageLog(Base):
    """企业微信群机器人消息发送日志"""

    __tablename__ = "enterprise_wechat_robot_message_log"
    __table_args__ = (
        Index("idx_ew_robot_log_config", "robot_config_id"),
        Index("idx_ew_robot_log_site_status", "site_id", "send_status"),
        {"comment": "v1.8 企业微信群机器人消息发送日志"},
    )

    robot_config_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("enterprise_wechat_robot_config.id"),
        nullable=False,
        comment="机器人配置ID",
    )
    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    message_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="text", server_default="text", comment="消息类型"
    )
    request_payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}", comment="发送请求体"
    )
    response_code: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="企业微信返回 errcode 或 HTTP 状态码"
    )
    response_body: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="企业微信返回体"
    )
    send_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="发送状态: success/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="失败原因"
    )

    robot_config: Mapped["EnterpriseWechatRobotConfig"] = relationship(
        back_populates="message_logs"
    )
