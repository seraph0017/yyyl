"""
通知相关 Schemas

- NotificationResponse：通知响应
- NotificationListParams：通知列表参数
"""


from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---- C端通知 ----

class NotificationResponse(BaseModel):
    """通知响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="通知ID")
    user_id: int = Field(description="用户ID")
    type: str = Field(description="通知类型")
    title: str = Field(description="标题")
    content: str = Field(description="内容")
    channel: str = Field(description="渠道: wechat_subscribe/in_app")
    related_type: Optional[str] = Field(default=None, description="关联类型: order/ticket等")
    related_id: Optional[int] = Field(default=None, description="关联ID")
    is_read: bool = Field(description="是否已读")
    send_status: str = Field(description="发送状态: pending/sent/failed")
    send_at: Optional[datetime] = Field(default=None, description="发送时间")
    created_at: datetime = Field(description="创建时间")


class NotificationListParams(BaseModel):
    """通知列表参数"""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, description="通知类型")
    is_read: Optional[bool] = Field(default=None, description="是否已读")
    channel: Optional[str] = Field(default=None, description="渠道")


class UnreadCountResponse(BaseModel):
    """未读通知计数"""

    model_config = ConfigDict(populate_by_name=True)

    count: int = Field(description="未读通知数量")


# ---- B端通知管理 ----

class NotificationTemplateResponse(BaseModel):
    """通知模板信息"""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="模板ID")
    name: str = Field(description="模板名称")
    type: str = Field(description="通知类型")
    channel: str = Field(description="默认渠道")
    enabled: bool = Field(description="是否启用")
    template_content: Optional[str] = Field(default=None, description="模板内容预览")


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板"""

    model_config = ConfigDict(populate_by_name=True)

    enabled: Optional[bool] = Field(default=None, description="是否启用")
    channel: Optional[str] = Field(default=None, description="默认渠道")


class NotificationRecordListParams(BaseModel):
    """通知发送记录查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    user_id: Optional[int] = Field(default=None, description="用户ID")
    type: Optional[str] = Field(default=None, description="通知类型")
    send_status: Optional[str] = Field(default=None, description="发送状态")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")


class TemplateStatItem(BaseModel):
    """模板统计项"""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(description="通知类型")
    name: str = Field(description="模板名称")
    subscribers: int = Field(description="订阅人数")
    total_sent: int = Field(description="总发送数")
    success_rate: float = Field(description="发送成功率(%)")


class SendTrendItem(BaseModel):
    """发送趋势项"""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="日期")
    sent: int = Field(description="发送数")
    success: int = Field(description="成功数")


class NotificationStatsResponse(BaseModel):
    """订阅统计数据"""

    model_config = ConfigDict(populate_by_name=True)

    total_subscriptions: int = Field(description="总订阅数")
    template_stats: list[TemplateStatItem] = Field(description="各模板统计")
    send_trend: list[SendTrendItem] = Field(description="近7天发送趋势")
    failed: int = Field(description="失败数")
