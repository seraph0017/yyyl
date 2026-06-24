"""
微信支付 APIv3 服务

负责：
- JSAPI 下单
- 小程序调起支付参数签名
- 支付/退款通知验签与 resource 解密
- 退款申请
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import settings

logger = logging.getLogger(__name__)

WECHAT_PAY_API_BASE = "https://api.mch.weixin.qq.com"


@dataclass(frozen=True)
class WechatPayConfig:
    app_id: str
    mch_id: str
    mch_serial_no: str
    api_v3_key: str
    private_key_pem: str
    platform_public_key_pem: str
    platform_public_key_id: str
    notify_url: str
    refund_notify_url: str


class WechatPayError(Exception):
    """微信支付调用异常"""


def get_wechat_pay_config(site_id: int = 1) -> WechatPayConfig:
    """读取微信支付配置。

    当前项目已有多营地微信登录映射；支付先使用统一商户号和默认小程序 AppID。
    如果后续每个营地独立商户，可在这里扩展 site_id 映射。
    """
    app_id = settings.WECHAT_APP_ID
    try:
        wechat_apps = json.loads(settings.WECHAT_APPS)
        app_config = wechat_apps.get(str(site_id))
        if app_config and app_config.get("app_id"):
            app_id = app_config["app_id"]
    except (json.JSONDecodeError, TypeError):
        pass

    api_v3_key = settings.WECHAT_API_V3_KEY or settings.WECHAT_API_KEY
    required = {
        "WECHAT_APP_ID": app_id,
        "WECHAT_MCH_ID": settings.WECHAT_MCH_ID,
        "WECHAT_MCH_SERIAL_NO": settings.WECHAT_MCH_SERIAL_NO,
        "WECHAT_API_V3_KEY": api_v3_key,
        "WECHAT_KEY_PATH": settings.WECHAT_KEY_PATH,
        "WECHAT_PLATFORM_PUBLIC_KEY_PATH": settings.WECHAT_PLATFORM_PUBLIC_KEY_PATH,
        "WECHAT_PLATFORM_PUBLIC_KEY_ID": settings.WECHAT_PLATFORM_PUBLIC_KEY_ID,
        "WECHAT_NOTIFY_URL": settings.WECHAT_NOTIFY_URL,
        "WECHAT_REFUND_NOTIFY_URL": settings.WECHAT_REFUND_NOTIFY_URL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise WechatPayError("微信支付配置缺失: " + ", ".join(missing))

    return WechatPayConfig(
        app_id=app_id,
        mch_id=settings.WECHAT_MCH_ID,
        mch_serial_no=settings.WECHAT_MCH_SERIAL_NO,
        api_v3_key=api_v3_key,
        private_key_pem=_read_text_file(settings.WECHAT_KEY_PATH, "商户 API 私钥"),
        platform_public_key_pem=_read_text_file(
            settings.WECHAT_PLATFORM_PUBLIC_KEY_PATH,
            "微信支付平台公钥",
        ),
        platform_public_key_id=settings.WECHAT_PLATFORM_PUBLIC_KEY_ID,
        notify_url=settings.WECHAT_NOTIFY_URL,
        refund_notify_url=settings.WECHAT_REFUND_NOTIFY_URL,
    )


async def create_jsapi_prepay(order: Any, site_id: int = 1) -> Dict[str, Any]:
    """调用微信支付 JSAPI 下单接口并返回小程序支付参数。"""
    config = get_wechat_pay_config(site_id)
    payload = {
        "appid": config.app_id,
        "mchid": config.mch_id,
        "description": f"一月一露订单 {order.order_no}",
        "out_trade_no": order.order_no,
        "notify_url": config.notify_url,
        "amount": {"total": _yuan_to_fen(order.actual_amount), "currency": "CNY"},
        "payer": {"openid": order.user.openid},
    }
    response = await _wechat_post(
        config,
        "/v3/pay/transactions/jsapi",
        payload,
    )
    prepay_id = response.get("prepay_id")
    if not prepay_id:
        raise WechatPayError("微信支付下单未返回 prepay_id")
    return build_mini_program_pay_params(config, prepay_id)


async def create_refund(
    order: Any,
    refund_amount: Decimal,
    reason: str | None = None,
    site_id: int = 1,
    out_refund_no: str | None = None,
) -> Dict[str, Any]:
    """申请微信支付退款。"""
    config = get_wechat_pay_config(site_id)
    out_refund_no = out_refund_no or f"R{order.order_no}{_utc_timestamp()}"
    payload = {
        "out_trade_no": order.order_no,
        "out_refund_no": out_refund_no,
        "reason": (reason or "用户退款")[:80],
        "notify_url": config.refund_notify_url,
        "amount": {
            "refund": _yuan_to_fen(refund_amount),
            "total": _yuan_to_fen(order.actual_amount),
            "currency": "CNY",
        },
    }
    return await _wechat_post(config, "/v3/refund/domestic/refunds", payload)


def build_mini_program_pay_params(
    config: WechatPayConfig,
    prepay_id: str,
    timestamp: Optional[str] = None,
    nonce_str: Optional[str] = None,
) -> Dict[str, str]:
    """生成 uni.requestPayment 所需参数。"""
    ts = timestamp or _utc_timestamp()
    nonce = nonce_str or _nonce_str()
    package = f"prepay_id={prepay_id}"
    message = f"{config.app_id}\n{ts}\n{nonce}\n{package}\n"
    return {
        "appId": config.app_id,
        "timeStamp": ts,
        "nonceStr": nonce,
        "package": package,
        "signType": "RSA",
        "paySign": _sign_with_private_key(config.private_key_pem, message),
    }


def decrypt_notification_resource(api_v3_key: str, resource: Dict[str, str]) -> Dict[str, Any]:
    """解密微信支付通知 resource。"""
    plaintext = AESGCM(api_v3_key.encode()).decrypt(
        resource["nonce"].encode(),
        base64.b64decode(resource["ciphertext"]),
        resource.get("associated_data", "").encode(),
    )
    return json.loads(plaintext.decode())


def verify_notification_signature(
    platform_public_key_pem: str,
    timestamp: str,
    nonce: str,
    body: str,
    signature: str,
) -> bool:
    """校验微信支付通知签名。"""
    public_key = serialization.load_pem_public_key(platform_public_key_pem.encode())
    message = f"{timestamp}\n{nonce}\n{body}\n".encode()
    try:
        public_key.verify(
            base64.b64decode(signature),
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False


async def parse_notification_body(body: str, headers: Dict[str, str], site_id: int = 1) -> Dict[str, Any]:
    """验签并解密微信支付通知。"""
    config = get_wechat_pay_config(site_id)
    timestamp = headers.get("Wechatpay-Timestamp") or headers.get("wechatpay-timestamp")
    nonce = headers.get("Wechatpay-Nonce") or headers.get("wechatpay-nonce")
    signature = headers.get("Wechatpay-Signature") or headers.get("wechatpay-signature")
    serial = headers.get("Wechatpay-Serial") or headers.get("wechatpay-serial")
    if serial and serial != config.platform_public_key_id:
        logger.warning("[微信支付] 回调平台公钥ID不匹配: serial=%s", serial)
    if not timestamp or not nonce or not signature:
        raise WechatPayError("微信支付通知缺少签名头")
    if not verify_notification_signature(config.platform_public_key_pem, timestamp, nonce, body, signature):
        raise WechatPayError("微信支付通知验签失败")
    payload = json.loads(body)
    resource = payload.get("resource")
    if not resource:
        raise WechatPayError("微信支付通知缺少 resource")
    return decrypt_notification_resource(config.api_v3_key, resource)


async def _wechat_post(config: WechatPayConfig, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = _utc_timestamp()
    nonce = _nonce_str()
    authorization = _build_authorization(config, "POST", path, timestamp, nonce, body)
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{WECHAT_PAY_API_BASE}{path}",
            content=body.encode(),
            headers={
                "Authorization": authorization,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
    if response.status_code >= 400:
        raise WechatPayError(f"微信支付请求失败({response.status_code}): {response.text}")
    return response.json()


def _build_authorization(
    config: WechatPayConfig,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: str,
) -> str:
    message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = _sign_with_private_key(config.private_key_pem, message)
    return (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{config.mch_id}",'
        f'nonce_str="{nonce}",'
        f'signature="{signature}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{config.mch_serial_no}"'
    )


def _sign_with_private_key(private_key_pem: str, message: str) -> str:
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    signature = private_key.sign(
        message.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def _read_text_file(path: str, label: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise WechatPayError(f"{label}读取失败: {path}") from exc


def _yuan_to_fen(value: Any) -> int:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


def _utc_timestamp() -> str:
    return str(int(datetime.now(timezone.utc).timestamp()))


def _nonce_str(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
