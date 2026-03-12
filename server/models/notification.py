"""
通知相关模型
- Notification（消息通知表）
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User


# ---- 枚举类型 ----

class NotificationChannel(str, enum.Enum):
    WECHAT_SUBSCRIBE = "wechat_subscribe"
    IN_APP = "in_app"


class SendStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ---- 模型 ----

class Notification(Base):
    """消息通知表"""

    __tablename__ = "notification"
    __table_args__ = (
        Index("idx_noti_user", "user_id"),
        Index("idx_noti_type", "type"),
        Index("idx_noti_read", "user_id", "is_read"),
        Index("idx_noti_related", "related_type", "related_id"),
        {"comment": "消息通知表"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="通知类型(13种)"
    )
    title: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="内容"
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="渠道: wechat_subscribe/in_app"
    )
    related_type: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="关联类型: order/ticket等"
    )
    related_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="关联ID"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="已读"
    )
    send_status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=SendStatus.PENDING.value,
        server_default=SendStatus.PENDING.value,
        comment="发送状态: pending/sent/failed"
    )
    send_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发送时间"
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="notifications")
