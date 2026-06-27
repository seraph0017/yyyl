"""
v1.8 企业微信群机器人服务
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any, Dict, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx


ENTERPRISE_WECHAT_ROBOT_HOST = "qyapi.weixin.qq.com"
ENTERPRISE_WECHAT_ROBOT_PATH = "/cgi-bin/webhook/send"


def validate_enterprise_wechat_webhook_url(webhook_url: str) -> None:
    """限制企业微信群机器人 webhook，避免 SSRF 和误配。"""
    split = urlsplit(webhook_url)
    if split.scheme != "https":
        raise ValueError("企业微信群机器人 webhook 必须使用 https")
    if split.hostname != ENTERPRISE_WECHAT_ROBOT_HOST:
        raise ValueError("企业微信群机器人 webhook 域名必须为 qyapi.weixin.qq.com")
    if split.path != ENTERPRISE_WECHAT_ROBOT_PATH:
        raise ValueError("企业微信群机器人 webhook 路径必须为 /cgi-bin/webhook/send")
    if split.fragment:
        raise ValueError("企业微信群机器人 webhook 不允许包含 fragment")

    query_pairs = parse_qsl(split.query, keep_blank_values=True)
    query = dict(query_pairs)
    if len(query_pairs) != 1 or not query.get("key"):
        raise ValueError("企业微信群机器人 webhook 必须包含 key")


def build_signed_webhook_url(
    webhook_url: str,
    *,
    secret: str | None = None,
    timestamp_ms: str | None = None,
) -> str:
    """按企业微信群机器人 secret 规则生成带签名的 webhook URL。"""
    if not secret:
        return webhook_url

    timestamp = timestamp_ms or str(int(time.time() * 1000))
    split = urlsplit(webhook_url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query["timestamp"] = timestamp
    query["sign"] = _build_robot_sign(secret=secret, timestamp_ms=timestamp)

    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def build_text_payload(
    content: str,
    *,
    mentioned_list: Iterable[str] | None = None,
    mentioned_mobile_list: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """生成企业微信群机器人 text 消息体。"""
    text: Dict[str, Any] = {"content": content}
    if mentioned_list is not None:
        text["mentioned_list"] = list(mentioned_list)
    if mentioned_mobile_list is not None:
        text["mentioned_mobile_list"] = list(mentioned_mobile_list)

    return {
        "msgtype": "text",
        "text": text,
    }


async def send_text_message(
    webhook_url: str,
    *,
    content: str,
    secret: str | None = None,
    mentioned_list: Iterable[str] | None = None,
    mentioned_mobile_list: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """发送企业微信群机器人 text 消息。"""
    validate_enterprise_wechat_webhook_url(webhook_url)
    signed_url = build_signed_webhook_url(webhook_url, secret=secret)
    payload = build_text_payload(
        content,
        mentioned_list=mentioned_list,
        mentioned_mobile_list=mentioned_mobile_list,
    )

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(signed_url, json=payload)
    body = response.json()
    return {
        "http_status": response.status_code,
        "body": body,
        "payload": payload,
    }


def _build_robot_sign(*, secret: str, timestamp_ms: str) -> str:
    raw = f"{timestamp_ms}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")
