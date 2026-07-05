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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---- 订单创建 ----

class OrderCreateItem(BaseModel):
    """订单项（创建订单时的单个商品项）"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID（多规格商品）")
    quantity: int = Field(ge=1, description="数量")
    dates: List[date] = Field(default_factory=list, description="预约日期列表（营位商品必填）")
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
    source_qrcode_id: Optional[int] = Field(default=None, description="来源小程序码ID")
    source_channel: Optional[str] = Field(default=None, max_length=64, description="来源渠道")
    source_scanned_at: Optional[datetime] = Field(default=None, description="来源扫码时间")

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_direct_order_payload(cls, data: Any) -> Any:
        """兼容旧小程序直购下单结构: product_id/dates/quantity。"""
        if not isinstance(data, dict) or "items" in data:
            return data

        if "product_id" not in data or "dates" not in data:
            return data

        item: dict[str, Any] = {
            "product_id": data["product_id"],
            "sku_id": data.get("sku_id"),
            "quantity": data.get("quantity", 1),
            "dates": data["dates"],
            "time_slot": data.get("time_slot"),
        }
        identity_ids = data.get("identity_ids")
        if identity_ids is None and data.get("identity_id") is not None:
            identity_ids = [data["identity_id"]]
        if identity_ids is not None:
            item["identity_ids"] = identity_ids

        normalized = data.copy()
        normalized["items"] = [item]
        normalized.setdefault("disclaimer_signed", True)
        return normalized

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        allowed = {"wechat_pay", "mock_pay", "annual_card_free", "times_card", "points_exchange"}
        if v not in allowed:
            raise ValueError(f"支付方式必须为 {allowed} 之一")
        return v


class OrderQuoteRequest(OrderCreateRequest):
    """订单确认页报价/库存预校验请求，不锁库存、不创建订单。"""


class OrderQuoteItemResponse(BaseModel):
    """订单报价项"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    product_name: str = Field(description="商品名称")
    date: Optional[DateType] = Field(default=None, description="预约日期")
    time_slot: Optional[str] = Field(default=None, description="场次")
    quantity: int = Field(description="数量")
    unit_price: Decimal = Field(description="单价")
    actual_price: Decimal = Field(description="小计")
    inventory_source: str = Field(description="库存来源: inventory/inventory_pool/none")
    inventory_pool_id: Optional[int] = Field(default=None, description="共享库存池ID")
    available: Optional[int] = Field(default=None, description="当前可用库存")


class OrderQuoteResponse(BaseModel):
    """订单确认页报价/库存预校验响应"""

    model_config = ConfigDict(populate_by_name=True)

    items: List[OrderQuoteItemResponse] = Field(default_factory=list, description="报价项")
    total_amount: Decimal = Field(description="商品金额")
    discount_amount: Decimal = Field(description="优惠金额")
    actual_amount: Decimal = Field(description="实付金额")
    deposit_amount: Decimal = Field(description="押金")
    discount_type: Optional[str] = Field(default=None, description="优惠类型")
    discount_detail: Optional[Dict[str, Any]] = Field(default=None, description="优惠明细")
    has_shared_inventory: bool = Field(default=False, description="是否命中共享库存池")


class SeckillOrderCreateRequest(BaseModel):
    """创建秒杀订单请求"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="秒杀商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    quantity: int = Field(default=1, ge=1, description="数量")
    booking_date: date = Field(description="预约日期")
    time_slot: Optional[str] = Field(default=None, max_length=20, description="场次")
    identity_ids: Optional[List[int]] = Field(default=None, description="出行人身份信息ID列表")
    disclaimer_signed: bool = Field(default=False, description="是否已签署免责声明")


class TemporaryOrderCreateRequest(BaseModel):
    """创建现场临时订单/收款会话请求"""

    model_config = ConfigDict(populate_by_name=True)

    payment_flow: str = Field(
        default="customer_scan_qr",
        description="收款方式: customer_scan_qr(顾客扫码)/merchant_scan_code(商户扫付款码)",
    )
    mode: Optional[str] = Field(default=None, description="模式: product/custom_amount；不传时按 product_id 自动推断")
    product_id: Optional[int] = Field(default=None, description="商品ID；商品临时单必填")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    quantity: int = Field(default=1, ge=1, le=999, description="数量")
    booking_date: Optional[date] = Field(default=None, description="预约日期")
    time_slot: Optional[str] = Field(default=None, max_length=20, description="场次")
    item_name: Optional[str] = Field(default=None, max_length=80, description="自定义收款项名称")
    amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.01"), description="自定义收款金额")
    remark: Optional[str] = Field(default=None, max_length=200, description="现场收款备注")
    auth_code: Optional[str] = Field(default=None, min_length=8, max_length=128, description="付款码授权码，仅商户扫付款码必填")
    device_id: Optional[str] = Field(default=None, max_length=64, description="收款设备标识")

    @model_validator(mode="after")
    def validate_temporary_order(self) -> "TemporaryOrderCreateRequest":
        if self.payment_flow not in {"customer_scan_qr", "merchant_scan_code"}:
            raise ValueError("收款方式必须为 customer_scan_qr 或 merchant_scan_code")

        inferred_mode = self.mode or ("product" if self.product_id else "custom_amount")
        if inferred_mode not in {"product", "custom_amount"}:
            raise ValueError("临时单模式必须为 product 或 custom_amount")
        self.mode = inferred_mode

        if inferred_mode == "product":
            if not self.product_id:
                raise ValueError("商品临时单必须选择商品")
            if self.amount is not None:
                raise ValueError("商品临时单金额必须由服务端按商品价格计算")
        else:
            if self.product_id or self.sku_id:
                raise ValueError("自定义金额临时单不能绑定商品或 SKU")
            if self.amount is None:
                raise ValueError("自定义金额临时单必须填写金额")
            if not (self.item_name or "").strip():
                raise ValueError("自定义金额临时单必须填写收款项名称")
            if not (self.remark or "").strip():
                raise ValueError("自定义金额临时单必须填写备注")

        if self.payment_flow == "merchant_scan_code" and not (self.auth_code or "").strip():
            raise ValueError("商户扫付款码必须提交付款码授权码")
        return self


# ---- 订单响应 ----

class OrderItemResponse(BaseModel):
    """订单项响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="订单项ID")
    order_id: int = Field(description="订单ID")
    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    inventory_pool_id: Optional[int] = Field(default=None, description="v1.8 订单锁定的共享库存池ID")
    date: Optional[DateType] = Field(default=None, description="预约日期")
    time_slot: Optional[str] = Field(default=None, description="场次")
    quantity: int = Field(description="数量")
    unit_price: Decimal = Field(description="原价")
    actual_price: Decimal = Field(description="折后实付")
    identity_id: Optional[int] = Field(default=None, description="出行人ID")
    parent_item_id: Optional[int] = Field(default=None, description="加人票关联原票")
    refund_status: str = Field(description="退款状态: none/pending/partial/refunded/rejected")
    created_at: datetime = Field(description="创建时间")

    # 关联显示字段（由 Service 层填充）
    product_name: Optional[str] = Field(default=None, description="商品名称")
    product_image: Optional[str] = Field(default=None, description="商品首图")
    cover_image: Optional[str] = Field(default=None, description="商品封面图")
    sku_spec_values: Optional[Dict[str, Any]] = Field(default=None, description="SKU 规格值")
    identity_name: Optional[str] = Field(default=None, description="出行人姓名")
    remark: Optional[str] = Field(default=None, description="订单项备注")


class OrderResponse(BaseModel):
    """订单响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="订单ID")
    order_no: str = Field(description="订单号")
    user_id: int = Field(description="用户ID")
    user_nickname: Optional[str] = Field(default=None, description="用户昵称")
    user_phone: Optional[str] = Field(default=None, description="用户手机号")
    user_phone_masked: Optional[str] = Field(default=None, description="脱敏用户手机号")
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


class TemporaryOrderSessionResponse(BaseModel):
    """现场临时订单/收款会话响应"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="会话ID")
    session_no: str = Field(description="临时会话号")
    token: Optional[str] = Field(default=None, description="扫码认领 Token，仅创建响应返回")
    status: str = Field(description="会话状态")
    payment_flow: str = Field(description="收款方式")
    mode: str = Field(description="模式")
    product_id: Optional[int] = Field(default=None, description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    quantity: int = Field(description="数量")
    booking_date: Optional[DateType] = Field(default=None, description="预约日期")
    time_slot: Optional[str] = Field(default=None, description="场次")
    item_name: Optional[str] = Field(default=None, description="自定义收款项名称")
    amount: Optional[Decimal] = Field(default=None, description="自定义金额")
    remark: Optional[str] = Field(default=None, description="备注")
    order_id: Optional[int] = Field(default=None, description="正式订单ID")
    expire_at: datetime = Field(description="过期时间")
    miniapp_path: Optional[str] = Field(default=None, description="顾客扫码进入的小程序路径")
    qrcode_image_url: Optional[str] = Field(default=None, description="顾客扫码小程序码图片地址")


class TemporaryOrderClaimResponse(BaseModel):
    """顾客扫码认领临时单响应"""

    model_config = ConfigDict(populate_by_name=True)

    order: OrderResponse = Field(description="正式订单")
    payment_params: Optional[Dict[str, Any]] = Field(default=None, description="微信 JSAPI 支付参数")


class TemporaryOrderCodePayResponse(BaseModel):
    """商户扫用户付款码收款响应"""

    model_config = ConfigDict(populate_by_name=True)

    session: TemporaryOrderSessionResponse = Field(description="临时会话")
    order: OrderResponse = Field(description="正式订单")
    trade_state: Optional[str] = Field(default=None, description="微信交易状态")
    transaction_id: Optional[str] = Field(default=None, description="微信支付订单号")
    requires_query: bool = Field(default=False, description="是否需要后续查单确认")


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
    product_id: Optional[int] = Field(default=None, description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID")
    product_type: Optional[str] = Field(default=None, description="商品类型/品类")
    booking_date_start: Optional[date] = Field(default=None, description="预约日期开始")
    booking_date_end: Optional[date] = Field(default=None, description="预约日期结束")
    time_slot: Optional[str] = Field(default=None, max_length=20, description="场次")
    payment_time_start: Optional[datetime] = Field(default=None, description="支付时间开始")
    payment_time_end: Optional[datetime] = Field(default=None, description="支付时间结束")
    amount_min: Optional[Decimal] = Field(default=None, ge=0, description="实付金额最小值")
    amount_max: Optional[Decimal] = Field(default=None, ge=0, description="实付金额最大值")
    verify_status: Optional[str] = Field(default=None, description="核销状态")
    source_channel: Optional[str] = Field(default=None, max_length=64, description="二维码来源渠道")


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

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_action(cls, data: Any) -> Any:
        """兼容旧小程序模拟支付参数: action=success/fail。"""
        if not isinstance(data, dict) or "success" in data:
            return data
        action = data.get("action")
        if action == "success":
            normalized = data.copy()
            normalized["success"] = True
            return normalized
        if action == "fail":
            normalized = data.copy()
            normalized["success"] = False
            return normalized
        return data


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
    qr_token: str = Field(default="", description="二维码Token，仅响应返回，不落库")
    qrcode_token: str = Field(default="", description="兼容小程序旧字段的二维码Token")
    qr_token_expires_at: datetime = Field(description="Token过期时间")
    verify_date: Optional[date] = Field(default=None, description="待验日期")
    date: Optional[DateType] = Field(default=None, description="兼容小程序旧字段的待验日期")
    verified_at: Optional[datetime] = Field(default=None, description="验票时间")
    verified_by: Optional[int] = Field(default=None, description="验票员")
    verify_status: str = Field(description="验票状态: pending/verified/expired")
    status: Optional[str] = Field(default=None, description="兼容小程序旧字段: unused/used/expired")
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
    qrcode_token: str = Field(default="", description="兼容小程序旧字段的二维码Token")
    qr_token_expires_at: datetime = Field(description="新的过期时间")


class TicketScanRequest(BaseModel):
    """员工扫码验票请求"""

    model_config = ConfigDict(populate_by_name=True)

    qr_token: str = Field(min_length=1, description="扫到的二维码Token")
    device_info: Optional[str] = Field(default=None, max_length=255, description="核销设备信息")


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


# ---- 员工端核销 ----

class StaffTicketSummary(BaseModel):
    """员工端票券摘要"""

    model_config = ConfigDict(populate_by_name=True)

    ticket_id: int = Field(description="票ID")
    ticket_no: str = Field(description="票号")
    ticket_type: str = Field(description="票类型")
    verify_status: str = Field(description="核销状态")
    verify_date: Optional[date] = Field(default=None, description="待核销日期")
    verified_at: Optional[datetime] = Field(default=None, description="核销时间")
    verified_by: Optional[int] = Field(default=None, description="核销员工ID")
    current_verify_count: int = Field(default=0, description="已核销次数")
    total_verify_count: int = Field(default=0, description="总核销次数")
    can_verify: bool = Field(default=False, description="当前是否可核销")


class StaffPendingTicketResponse(BaseModel):
    """员工端待核销票券"""

    model_config = ConfigDict(populate_by_name=True)

    ticket_id: int
    ticket_no: str
    ticket_type: str
    order_id: int
    order_no: str
    order_item_id: Optional[int] = None
    user_id: int
    user_nickname: Optional[str] = None
    user_phone_masked: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int = 1
    date: Optional[date] = None
    time_slot: Optional[str] = None
    verify_date: Optional[date] = None
    verify_status: str
    current_verify_count: int = 0
    total_verify_count: int = 0
    can_verify: bool = True
    actual_amount: Decimal
    remark: Optional[str] = None


class StaffTodayOrderResponse(BaseModel):
    """员工端今日订单行"""

    model_config = ConfigDict(populate_by_name=True)

    order_id: int
    order_no: str
    status: str
    payment_status: str
    payment_time: Optional[datetime] = None
    actual_amount: Decimal
    user_id: int
    user_nickname: Optional[str] = None
    user_phone_masked: Optional[str] = None
    order_item_id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    date: Optional[date] = None
    time_slot: Optional[str] = None
    verify_status: str
    ticket_id: Optional[int] = None
    ticket_no: Optional[str] = None
    can_verify: bool = False
    remark: Optional[str] = None


class StaffTicketLogResponse(BaseModel):
    """员工端核销历史"""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    ticket_id: Optional[int] = None
    ticket_no: Optional[str] = None
    order_id: Optional[int] = None
    order_no: Optional[str] = None
    order_item_id: Optional[int] = None
    product_name: Optional[str] = None
    verify_date: Optional[date] = None
    quantity: Optional[int] = None
    time_slot: Optional[str] = None
    user_nickname: Optional[str] = None
    user_phone_masked: Optional[str] = None
    staff_id: int
    staff_source: str = "user"
    verify_result: str
    failure_reason: Optional[str] = None
    device_info: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime


class StaffOrderItemResponse(BaseModel):
    """员工端订单详情项"""

    model_config = ConfigDict(populate_by_name=True)

    order_item_id: int
    product_id: int
    sku_id: Optional[int] = None
    product_name: Optional[str] = None
    product_image: Optional[str] = None
    quantity: int
    date: Optional[date] = None
    time_slot: Optional[str] = None
    unit_price: Decimal
    actual_price: Decimal
    tickets: List[StaffTicketSummary] = Field(default_factory=list)


class StaffOrderDetailResponse(BaseModel):
    """员工端订单详情"""

    model_config = ConfigDict(populate_by_name=True)

    order_id: int
    order_no: str
    user_id: int
    user_nickname: Optional[str] = None
    user_phone_masked: Optional[str] = None
    status: str
    payment_status: str
    payment_method: str
    payment_time: Optional[datetime] = None
    total_amount: Decimal
    actual_amount: Decimal
    discount_amount: Decimal
    remark: Optional[str] = None
    created_at: datetime
    items: List[StaffOrderItemResponse] = Field(default_factory=list)
