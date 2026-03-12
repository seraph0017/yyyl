"""
通用工具函数

- generate_order_no：订单号生成
- generate_ticket_code：验票码生成
- generate_verification_code：验证码生成
- format_price：价格格式化
"""


import random
import string
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


def generate_order_no(prefix: str = "YY") -> str:
    """生成订单号

    格式：{prefix}{日期yyyyMMdd}{时间HHmmss}{4位随机数}
    示例：YY20260312143025_8527

    Args:
        prefix: 订单号前缀，默认 "YY"（某露营地）

    Returns:
        唯一订单号（约24位）
    """
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d%H%M%S")
    random_part = f"{random.randint(1000, 9999)}"
    return f"{prefix}{date_part}{random_part}"


def generate_ticket_code() -> str:
    """生成验票码（电子票票号）

    格式：TK + 12位字母数字
    示例：TK4A7B3C9D1E2F

    Returns:
        唯一票号（14位）
    """
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(random.choices(chars, k=12))
    return f"TK{random_part}"


def generate_verification_code(length: int = 6) -> str:
    """生成数字验证码

    Args:
        length: 验证码位数，默认6位

    Returns:
        纯数字验证码
    """
    return "".join(random.choices(string.digits, k=length))


def generate_qr_token() -> str:
    """生成二维码 Token（30秒刷新用）

    基于 UUID4 + 时间戳，确保唯一性

    Returns:
        32位十六进制字符串
    """
    return uuid.uuid4().hex


def generate_batch_no() -> str:
    """生成批次号（激活码批次）

    格式：BA{日期}{6位随机}
    示例：BA202603121A2B3C

    Returns:
        批次号
    """
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(random.choices(chars, k=6))
    return f"BA{date_part}{random_part}"


def generate_transaction_no(prefix: str = "TX") -> str:
    """生成交易流水号

    Args:
        prefix: 前缀，默认 "TX"

    Returns:
        交易流水号
    """
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d%H%M%S")
    random_part = f"{random.randint(100000, 999999)}"
    return f"{prefix}{date_part}{random_part}"


def format_price(amount: Decimal, symbol: str = "¥") -> str:
    """格式化价格（保留两位小数）

    Args:
        amount: 金额
        symbol: 货币符号，默认人民币 ¥

    Returns:
        格式化后的价格字符串，如 ¥128.00
    """
    rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{symbol}{rounded}"


def yuan_to_fen(amount: Decimal) -> int:
    """元转分（微信支付用）

    Args:
        amount: 金额（元）

    Returns:
        金额（分）
    """
    return int(amount * 100)


def fen_to_yuan(amount: int) -> Decimal:
    """分转元

    Args:
        amount: 金额（分）

    Returns:
        金额（元）
    """
    return Decimal(amount) / 100


def generate_activation_code(length: int = 16) -> str:
    """生成激活码（大写字母+数字）

    Args:
        length: 激活码长度，默认16位

    Returns:
        激活码字符串
    """
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))
