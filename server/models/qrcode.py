"""
小程序码相关模型
- MiniProgramQRCode：小程序码主表
- MiniProgramQRCodeScanLog：扫码日志
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class MiniProgramQRCode(Base):
    """微信小程序码主表"""

    __tablename__ = "mini_program_qrcode"
    __table_args__ = (
        Index(
            "uq_qrcode_site_target_channel_scene",
            "site_id",
            "target_type",
            "target_key",
            "channel",
            "scene",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_qrcode_short_code", "short_code", unique=True),
        Index("idx_qrcode_site_status", "site_id", "status"),
        {"comment": "小程序码主表"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1", comment="营地ID"
    )
    target_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="目标类型"
    )
    target_key: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="目标ID或页面标识"
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="二维码标题"
    )
    path: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="小程序内部跳转路径"
    )
    scene: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="微信 scene 参数"
    )
    short_code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, comment="短码"
    )
    channel: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", server_default="default",
        comment="渠道"
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="二维码图片URL"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active",
        comment="状态: active/inactive"
    )
    generated_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="生成管理员ID"
    )
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="生成时间"
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近扫码时间"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="扫码次数"
    )

    scan_logs: Mapped[list["MiniProgramQRCodeScanLog"]] = relationship(
        back_populates="qrcode", lazy="noload"
    )


class MiniProgramQRCodeScanLog(Base):
    """小程序码扫码日志"""

    __tablename__ = "mini_program_qrcode_scan_log"
    __table_args__ = (
        Index("idx_qrcode_scan_qr_time", "qr_code_id", "scanned_at"),
        Index("idx_qrcode_scan_site_time", "site_id", "scanned_at"),
        {"comment": "小程序码扫码日志"},
    )

    site_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="营地ID"
    )
    qr_code_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("mini_program_qrcode.id"), nullable=False,
        comment="二维码ID"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="用户ID"
    )
    openid: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="微信 openid"
    )
    channel: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="渠道"
    )
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="扫码时间"
    )
    raw_scene: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="原始 scene"
    )
    client_info: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="客户端信息"
    )

    qrcode: Mapped[MiniProgramQRCode] = relationship(
        back_populates="scan_logs", lazy="noload"
    )
