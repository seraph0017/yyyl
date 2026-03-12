"""
管理端相关 Schemas

- AdminUserCreate / AdminUserUpdate / AdminUserResponse：管理员 CRUD
- DashboardOverview：Dashboard 概览
- SalesReportParams / SalesReportResponse：销售报表
- OperationLogResponse：操作日志
"""

import datetime as _dt
from datetime import date, datetime

DateType = _dt.date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 管理员 CRUD ----

class AdminUserCreate(BaseModel):
    """创建管理员"""

    model_config = ConfigDict(populate_by_name=True)

    username: Optional[str] = Field(default=None, max_length=50, description="用户名")
    password: Optional[str] = Field(default=None, min_length=6, max_length=128, description="密码")
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    real_name: Optional[str] = Field(default=None, max_length=50, description="真实姓名")
    role_id: int = Field(description="角色ID")
    user_id: Optional[int] = Field(default=None, description="关联微信用户ID")


class AdminUserUpdate(BaseModel):
    """更新管理员"""

    model_config = ConfigDict(populate_by_name=True)

    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    real_name: Optional[str] = Field(default=None, max_length=50, description="真实姓名")
    role_id: Optional[int] = Field(default=None, description="角色ID")
    status: Optional[str] = Field(default=None, description="状态: active/disabled")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


class AdminUserResponse(BaseModel):
    """管理员信息响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="管理员ID")
    user_id: Optional[int] = Field(default=None, description="关联用户ID")
    username: Optional[str] = Field(default=None, description="用户名")
    phone: Optional[str] = Field(default=None, description="手机号（脱敏）")
    real_name: Optional[str] = Field(default=None, description="真实姓名")
    role_id: Optional[int] = Field(default=None, description="角色ID")
    status: str = Field(description="状态")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")
    created_at: datetime = Field(description="创建时间")

    # 关联
    role_name: Optional[str] = Field(default=None, description="角色名称")
    role_code: Optional[str] = Field(default=None, description="角色代码")
    permissions: List[str] = Field(default_factory=list, description="权限列表")

    @field_validator("phone", mode="before")
    @classmethod
    def mask_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) >= 11:
            return f"{v[:3]}****{v[-4:]}"
        return v


# ---- 角色权限 ----

class PermissionSchema(BaseModel):
    """权限信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="权限ID")
    resource: str = Field(description="资源")
    action: str = Field(description="操作")


class PermissionItem(BaseModel):
    """权限项"""

    model_config = ConfigDict(populate_by_name=True)

    resource: str = Field(description="资源")
    action: str = Field(description="操作: read/write/delete/export")


class RoleResponse(BaseModel):
    """角色信息"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="角色ID")
    role_name: str = Field(description="角色名称")
    role_code: str = Field(description="角色代码")
    description: Optional[str] = Field(default=None, description="描述")
    permissions: List[PermissionSchema] = Field(default_factory=list, description="权限列表")


class PermissionUpdateRequest(BaseModel):
    """更新角色权限请求"""

    model_config = ConfigDict(populate_by_name=True)

    permissions: List[PermissionItem] = Field(description="权限列表")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


# ---- Dashboard ----

class DashboardOverview(BaseModel):
    """Dashboard 概览数据"""

    model_config = ConfigDict(populate_by_name=True)

    # 实时数据卡片
    today_orders: int = Field(description="今日订单数")
    today_revenue: Decimal = Field(description="今日收入")
    today_visitors: int = Field(description="今日在营人数")
    inventory_alerts: int = Field(description="库存告警数")

    # 同比环比
    yesterday_orders: Optional[int] = Field(default=None, description="昨日订单数")
    yesterday_revenue: Optional[Decimal] = Field(default=None, description="昨日收入")
    order_growth_rate: Optional[Decimal] = Field(default=None, description="订单环比增长率(%)")
    revenue_growth_rate: Optional[Decimal] = Field(default=None, description="收入环比增长率(%)")


class TrendDataPoint(BaseModel):
    """趋势图数据点"""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="日期")
    orders: int = Field(description="订单数")
    revenue: Decimal = Field(description="收入")


class TrendDataResponse(BaseModel):
    """趋势图数据"""

    model_config = ConfigDict(populate_by_name=True)

    period: str = Field(description="时间范围: 7d/30d")
    data: List[TrendDataPoint] = Field(description="数据点列表")


class SalesRankingItem(BaseModel):
    """销售排行项"""

    model_config = ConfigDict(populate_by_name=True)

    rank: int = Field(description="排名")
    product_id: int = Field(description="商品ID")
    product_name: str = Field(description="商品名称")
    product_type: str = Field(description="商品类型")
    sales_count: int = Field(description="销量")
    sales_amount: Decimal = Field(description="销售额")


class MemberStatsResponse(BaseModel):
    """会员数据统计"""

    model_config = ConfigDict(populate_by_name=True)

    total_users: int = Field(description="总用户数")
    total_members: int = Field(description="会员数")
    annual_card_active: int = Field(description="有效年卡数")
    times_card_active: int = Field(description="有效次数卡数")
    new_users_today: int = Field(description="今日新增用户")
    new_members_today: int = Field(description="今日新增会员")
    member_conversion_rate: Optional[Decimal] = Field(default=None, description="会员转化率(%)")


class HeatmapItem(BaseModel):
    """热力图数据项"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    product_name: str = Field(description="商品名称")
    report_date: date = Field(description="日期")
    total: int = Field(description="总库存")
    sold: int = Field(description="已售")
    occupancy_rate: Decimal = Field(description="入住率(%)")


class HeatmapDataResponse(BaseModel):
    """营位预定热力图数据"""

    model_config = ConfigDict(populate_by_name=True)

    date_start: date = Field(description="开始日期")
    date_end: date = Field(description="结束日期")
    data: List[HeatmapItem] = Field(description="热力图数据")


class FinanceSummaryResponse(BaseModel):
    """财务概览"""

    model_config = ConfigDict(populate_by_name=True)

    pending_amount: Decimal = Field(description="待确认金额")
    available_amount: Decimal = Field(description="可提现金额")
    deposit_amount: Decimal = Field(description="押金专户")
    maintenance_income: Decimal = Field(description="设备维护收入")
    today_income: Decimal = Field(description="今日收入")
    today_refund: Decimal = Field(description="今日退款")
    month_income: Decimal = Field(description="本月收入")
    month_refund: Decimal = Field(description="本月退款")
    mom_income_growth: Optional[Decimal] = Field(default=None, description="收入月环比(%)")
    yoy_income_growth: Optional[Decimal] = Field(default=None, description="收入同比(%)")


class CategoryRevenueItem(BaseModel):
    """品类收入占比项"""

    model_config = ConfigDict(populate_by_name=True)

    category: str = Field(description="品类")
    revenue: Decimal = Field(description="收入")
    percentage: Decimal = Field(description="占比(%)")
    orders: int = Field(description="订单数")


# ---- 销售报表 ----

class SalesReportParams(BaseModel):
    """销售报表查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    granularity: str = Field(default="day", description="粒度: day/week/month")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")
    category: Optional[str] = Field(default=None, description="品类筛选")

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        if v not in ("day", "week", "month"):
            raise ValueError("粒度必须为 day/week/month")
        return v


class SalesReportDetail(BaseModel):
    """销售报表明细"""

    model_config = ConfigDict(populate_by_name=True)

    period: str = Field(description="时间段")
    orders: int = Field(description="订单数")
    revenue: Decimal = Field(description="收入")
    refund: Decimal = Field(description="退款")
    net: Decimal = Field(description="净收入")
    avg_amount: Optional[Decimal] = Field(default=None, description="客单价")


class SalesReportResponse(BaseModel):
    """销售报表响应"""

    model_config = ConfigDict(populate_by_name=True)

    period: str = Field(description="统计周期描述")
    total_orders: int = Field(description="总订单数")
    total_revenue: Decimal = Field(description="总收入")
    refund_amount: Decimal = Field(description="退款金额")
    net_revenue: Decimal = Field(description="净收入")
    avg_order_amount: Optional[Decimal] = Field(default=None, description="平均客单价")
    mom_growth: Optional[Decimal] = Field(default=None, description="环比增长(%)")
    yoy_growth: Optional[Decimal] = Field(default=None, description="同比增长(%)")
    details: List[SalesReportDetail] = Field(default_factory=list, description="明细数据")


# ---- 操作日志 ----

class OperationLogResponse(BaseModel):
    """操作日志响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="日志ID")
    operator_id: int = Field(description="操作人ID")
    operator_name: str = Field(description="操作人姓名")
    action: str = Field(description="操作")
    target_type: str = Field(description="目标类型")
    target_id: Optional[int] = Field(default=None, description="目标ID")
    detail: Optional[Dict[str, Any]] = Field(default=None, description="变更前后值")
    ip_address: Optional[str] = Field(default=None, description="IP地址")
    is_high_risk: bool = Field(description="是否高风险操作")
    confirm_result: Optional[str] = Field(default=None, description="确认结果")
    created_at: datetime = Field(description="操作时间")


class OperationLogListParams(BaseModel):
    """操作日志查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    operator_id: Optional[int] = Field(default=None, description="操作人ID")
    action: Optional[str] = Field(default=None, description="操作类型")
    target_type: Optional[str] = Field(default=None, description="目标类型")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")
    is_high_risk: Optional[bool] = Field(default=None, description="仅高风险")


# ---- 二次确认 ----

class ConfirmVerifyCodeRequest(BaseModel):
    """验证操作确认码请求"""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(min_length=6, max_length=6, description="6位确认码")
    action: str = Field(description="待确认操作标识")


class ConfirmVerifyPasswordRequest(BaseModel):
    """验证管理员操作密码请求"""

    model_config = ConfigDict(populate_by_name=True)

    password: str = Field(min_length=1, description="操作密码")
    action: str = Field(description="待确认操作标识")


class ConfirmResponse(BaseModel):
    """确认结果响应"""

    model_config = ConfigDict(populate_by_name=True)

    confirmed: bool = Field(description="是否确认通过")
    confirm_token: Optional[str] = Field(default=None, description="确认Token（用于后续操作）")
    message: Optional[str] = Field(default=None, description="消息")


# ---- 营地日历 ----

class CalendarQuery(BaseModel):
    """营地日历查询参数"""

    model_config = ConfigDict(populate_by_name=True)

    date_start: date = Field(description="开始日期")
    date_end: date = Field(description="结束日期")
    product_ids: Optional[List[int]] = Field(default=None, description="商品ID筛选")


class CalendarCell(BaseModel):
    """日历单元格数据"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    product_name: str = Field(description="商品名称")
    date: DateType = Field(description="日期")
    date_type: str = Field(description="日期类型")
    price: Decimal = Field(description="价格")
    total: int = Field(description="总库存")
    available: int = Field(description="可用库存")
    sold: int = Field(description="已售")
    locked: int = Field(description="锁定")
    status: str = Field(description="库存状态")


class CalendarResponse(BaseModel):
    """营地日历响应"""

    model_config = ConfigDict(populate_by_name=True)

    date_start: date = Field(description="开始日期")
    date_end: date = Field(description="结束日期")
    cells: List[CalendarCell] = Field(description="日历数据矩阵")


# ---- 数据报表 ----

class ReportExportRequest(BaseModel):
    """报表导出请求"""

    model_config = ConfigDict(populate_by_name=True)

    report_type: str = Field(description="报表类型: sales/users/products")
    granularity: str = Field(default="day", description="粒度: day/week/month")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")
    category: Optional[str] = Field(default=None, description="品类")

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        if v not in ("sales", "users", "products"):
            raise ValueError("报表类型必须为 sales/users/products")
        return v


class ReportExportResponse(BaseModel):
    """报表导出响应"""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(description="异步任务ID")
    status: str = Field(description="状态: pending/processing/completed/failed")
    download_url: Optional[str] = Field(default=None, description="下载链接")


# ---- 订单导出 ----

class OrderExportRequest(BaseModel):
    """导出订单数据请求"""

    model_config = ConfigDict(populate_by_name=True)

    status: Optional[str] = Field(default=None, description="订单状态")
    order_type: Optional[str] = Field(default=None, description="订单类型")
    date_start: Optional[date] = Field(default=None, description="开始日期")
    date_end: Optional[date] = Field(default=None, description="结束日期")
    include_address: bool = Field(default=False, description="是否包含收货地址")
