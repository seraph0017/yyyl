"""
订单相关 Schemas

- OrderCreateRequest / OrderCreateItem：创建订单
- OrderResponse / OrderItemResponse：订单响应
- OrderListParams：订单列表筛选参数
- RefundRequest：退票请求
- TicketResponse：电子票响应
"""

import datetime as _dt
from datetime import date, datetime

DateType = _dt.date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- 订单创建 ----

class OrderCreateItem(BaseModel):
    """订单项（创建订单时的单个商品项）"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID（多规格商品）")
    quantity: int = Field(ge=1, description="数量")
    dates: List[date] = Field(min_length=1, description="预约日期列表（多日票传多个日期）")
    time_slot: Optional[str] = Field(default=None, max_length=20, description="场次（活动类）")
    identity_ids: Optional[List[int]] = Field(default=None, description="出行人身份信息ID列表")
    parent_order_item_id: Optional[int] = Field(
        default=None,
        description="加人票关联原订单项ID（加人票专用）",
    )


class OrderCreateRequest(BaseModel):
    """创建普通订单请求"""

    model_config = ConfigDict(populate_by_name=True)

    items: List[OrderCreateItem] = Field(min_length=1, description="订单项列表")
    disclaimer_signed: bool = Field(default=False, description="是否已签署免责声明")
    disclaimer_template_id: Optional[int] = Field(default=None, description="免责声明模板ID")
    address_id: Optional[int] = Field(default=None, description="收货地址ID（周边商品/邮寄）")
    remark: Optional[str] = Field(default=None, max_length=200, description="备注")
    payment_method: str = Field(default="wechat_pay", description="支付方式: wechat_pay/mock_pay")
    times_card_id: Optional[int] = Field(default=None, description="使用的次数卡ID")

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        allowed = {"wechat_pay", "mock_pay", "annual_card_free", "times_card", "points_exchange"}
        if v not in allowed:
            raise ValueError(f"支付方式必须为 {allowed} 之一")
        return v


class SeckillOrderCreateRequest(BaseModel):
    """创建秒杀订单请求"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="秒杀商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    quantity: int = Field(default=1, ge=1, description="数量")
    booking_date: date = Field(description="预约日期")
    identity_ids: Optional[List[int]] = Field(default=None, description="出行人身份信息ID列表")
    disclaimer_signed: bool = Field(default=False, description="是否已签署免责声明")


# ---- 订单响应 ----

class OrderItemResponse(BaseModel):
    """订单项响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="订单项ID")
    order_id: int = Field(description="订单ID")
    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    date: Optional[DateType] = Field(default=None, description="预约日期")
    time_slot: Optional[str] = Field(default=None, description="场次")
    quantity: int = Field(description="数量")
    unit_price: Decimal = Field(description="原价")
    actual_price: Decimal = Field(description="折后实付")
    identity_id: Optional[int] = Field(default=None, description="出行人ID")
    parent_item_id: Optional[int] = Field(default=None, description="加人票关联原票")
    refund_status: str = Field(description="退款状态: none/refunded")
    created_at: datetime = Field(description="创建时间")

    # 关联显示字段（由 Service 层填充）
    product_name: Optional[str] = Field(default=None, description="商品名称")
    product_image: Optional[str] = Field(default=None, description="商品首图")
    sku_spec_values: Optional[Dict[str, Any]] = Field(default=None, description="SKU 规格值")
    identity_name: Optional[str] = Field(default=None, description="出行人姓名")


class OrderResponse(BaseModel):
    """订单响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="订单ID")
    order_no: str = Field(description="订单号")
    user_id: int = Field(description="用户ID")
    parent_order_id: Optional[int] = Field(default=None, description="父订单ID")
    order_type: str = Field(description="订单类型")
    status: str = Field(description="订单状态")
    total_amount: Decimal = Field(description="总金额")
    discount_amount: Decimal = Field(description="优惠金额")
    actual_amount: Decimal = Field(description="实付金额")
    deposit_amount: Decimal = Field(default=Decimal("0"), description="押金")
    discount_type: Optional[str] = Field(default=None, description="优惠类型")
    discount_detail: Optional[Dict[str, Any]] = Field(default=None, description="优惠明细")
    payment_method: str = Field(description="支付方式")
    payment_status: str = Field(description="支付状态")
    payment_time: Optional[datetime] = Field(default=None, description="支付时间")
    payment_no: Optional[str] = Field(default=None, description="支付流水号")
    times_card_id: Optional[int] = Field(default=None, description="次数卡ID")
    times_consumed: Optional[int] = Field(default=None, description="消耗次数")
    address_id: Optional[int] = Field(default=None, description="收货地址ID")
    shipping_no: Optional[str] = Field(default=None, description="物流单号")
    shipping_status: Optional[str] = Field(default=None, description="物流状态")
    remark: Optional[str] = Field(default=None, description="备注")
    expire_at: Optional[datetime] = Field(default=None, description="支付截止时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    # 关联
    items: List[OrderItemResponse] = Field(default_factory=list, description="订单项列表")

    # 聚合字段（由 Service 层填充）
    countdown_seconds: Optional[int] = Field(default=None, description="支付倒计时（秒）")


# ---- 订单列表筛选 ----

class OrderListParams(BaseModel):
    """订单列表筛选参数"""

    model_config = ConfigDict(populate_by_name=True)

    status: Optional[str] = Field(default=None, description="订单状态筛选")
    order_type: Optional[str] = Field(default=None, description="订单类型")
    date_start: Optional[date] = Field(default=None, description="下单日期开始")
    date_end: Optional[date] = Field(default=None, description="下单日期结束")
    keyword: Optional[str] = Field(default=None, max_length=50, description="搜索关键词（订单号/商品名）")
    payment_status: Optional[str] = Field(default=None, description="支付状态")
    user_id: Optional[int] = Field(default=None, description="用户ID（管理端）")


# ---- 订单操作 ----

class OrderCancelRequest(BaseModel):
    """取消订单（仅限待支付状态）"""

    model_config = ConfigDict(populate_by_name=True)

    reason: Optional[str] = Field(default=None, max_length=200, description="取消原因")


class RefundRequest(BaseModel):
    """退票请求"""

    model_config = ConfigDict(populate_by_name=True)

    reason: Optional[str] = Field(default=None, max_length=200, description="退票原因")
    order_item_ids: Optional[List[int]] = Field(
        default=None,
        description="指定退票的订单项ID（为空则全额退票）",
    )


class RefundApproveRequest(BaseModel):
    """审批退款请求（管理端）"""

    model_config = ConfigDict(populate_by_name=True)

    approved: bool = Field(description="是否通过")
    reject_reason: Optional[str] = Field(default=None, max_length=200, description="拒绝原因")


class PartialRefundRequest(BaseModel):
    """手动部分退票请求（管理端）"""

    model_config = ConfigDict(populate_by_name=True)

    order_item_ids: List[int] = Field(min_length=1, description="退票的订单项ID列表")
    reason: Optional[str] = Field(default=None, max_length=200, description="退款原因")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


class BatchRefundRequest(BaseModel):
    """批量退款请求"""

    model_config = ConfigDict(populate_by_name=True)

    order_ids: List[int] = Field(min_length=1, description="订单ID列表")
    reason: Optional[str] = Field(default=None, max_length=200, description="退款原因")
    confirm_code: Optional[str] = Field(default=None, description="二次确认码")


class ShippingUpdateRequest(BaseModel):
    """更新物流信息"""

    model_config = ConfigDict(populate_by_name=True)

    shipping_no: str = Field(min_length=1, max_length=64, description="物流单号")
    shipping_company: Optional[str] = Field(default=None, max_length=50, description="物流公司")


# ---- 支付相关 ----

class PaymentRequest(BaseModel):
    """发起支付请求"""

    model_config = ConfigDict(populate_by_name=True)

    payment_method: str = Field(default="wechat_pay", description="支付方式: wechat_pay/mock_pay")


class MockPayRequest(BaseModel):
    """模拟支付请求"""

    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(default=True, description="模拟成功或失败")


class PaymentCallbackData(BaseModel):
    """微信支付回调数据（简化）"""

    model_config = ConfigDict(populate_by_name=True)

    out_trade_no: str = Field(description="商户订单号")
    transaction_id: str = Field(description="微信支付订单号")
    total_fee: int = Field(description="支付金额（分）")
    result_code: str = Field(description="支付结果: SUCCESS/FAIL")


class WxPayResponse(BaseModel):
    """微信支付调起参数"""

    model_config = ConfigDict(populate_by_name=True)

    appId: str = Field(description="小程序appId")
    timeStamp: str = Field(description="时间戳")
    nonceStr: str = Field(description="随机字符串")
    package: str = Field(description="统一下单接口返回的 prepay_id")
    signType: str = Field(default="RSA", description="签名类型")
    paySign: str = Field(description="签名")


# ---- 电子票 ----

class TicketResponse(BaseModel):
    """电子票响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="票ID")
    order_id: int = Field(description="订单ID")
    order_item_id: Optional[int] = Field(default=None, description="订单项ID")
    user_id: int = Field(description="用户ID")
    ticket_no: str = Field(description="票号")
    ticket_type: str = Field(description="票类型: camping/rental/activity")
    qr_token: str = Field(description="二维码Token")
    qr_token_expires_at: datetime = Field(description="Token过期时间")
    verify_date: Optional[date] = Field(default=None, description="待验日期")
    verified_at: Optional[datetime] = Field(default=None, description="验票时间")
    verified_by: Optional[int] = Field(default=None, description="验票员")
    verify_status: str = Field(description="验票状态: pending/verified/expired")
    total_verify_count: int = Field(description="总验次数")
    current_verify_count: int = Field(description="已验次数")
    created_at: datetime = Field(description="创建时间")

    # 关联显示字段
    product_name: Optional[str] = Field(default=None, description="商品名称")
    product_image: Optional[str] = Field(default=None, description="商品首图")


class TicketRefreshResponse(BaseModel):
    """刷新二维码 Token 响应"""

    model_config = ConfigDict(populate_by_name=True)

    ticket_id: int = Field(description="票ID")
    qr_token: str = Field(description="新的二维码Token")
    qr_token_expires_at: datetime = Field(description="新的过期时间")


class TicketScanRequest(BaseModel):
    """员工扫码验票请求"""

    model_config = ConfigDict(populate_by_name=True)

    qr_token: str = Field(min_length=1, description="扫到的二维码Token")


class TicketScanResponse(BaseModel):
    """扫码验票响应"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(description="验票会话ID")
    ticket_id: int = Field(description="票ID")
    ticket_no: str = Field(description="票号")
    ticket_type: str = Field(description="票类型")
    product_name: Optional[str] = Field(default=None, description="商品名称")
    verify_date: Optional[date] = Field(default=None, description="待验日期")
    needs_verification_code: bool = Field(description="是否需要年卡验证码")
    verification_code: Optional[str] = Field(default=None, description="验证码（年卡场景下发给用户）")


class VerifyCodeRequest(BaseModel):
    """年卡验证码验证请求"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(description="验票会话ID")
    code: str = Field(min_length=6, max_length=6, description="6位验证码")


class VerifyStatusResponse(BaseModel):
    """验票状态轮询响应"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(description="验票会话ID")
    status: str = Field(description="状态: waiting/code_sent/verified/failed/expired")
    verification_code: Optional[str] = Field(default=None, description="验证码（用户端显示）")
    message: Optional[str] = Field(default=None, description="状态消息")
