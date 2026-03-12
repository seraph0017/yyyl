"""
安全工具模块

- JWT Token 创建 & 验证
- 密码哈希 & 验证
- AES-256 加密 & 解密（敏感数据保护）
"""


import base64
import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
import bcrypt
from jose import JWTError, jwt

from config import settings

# ---- 密码哈希 ----


def hash_password(password: str) -> str:
    """密码哈希（bcrypt）

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        密码是否匹配
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---- JWT Token ----

# access_token 有效期（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2小时
# refresh_token 有效期（天）
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """生成 access_token

    Args:
        data: 载荷数据，须包含 sub（user_id）和 role
        expires_delta: 自定义过期时间（默认2小时）

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "token_type": "access",
        "jti": uuid.uuid4().hex,
    })

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """生成 refresh_token

    Args:
        data: 载荷数据
        expires_delta: 自定义过期时间（默认7天）

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "token_type": "refresh",
        "jti": uuid.uuid4().hex,
    })

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> Dict[str, Any]:
    """验证 JWT Token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的载荷字典

    Raises:
        JWTError: Token 无效或已过期
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise


def get_token_expire_seconds(token_type: str = "access") -> int:
    """获取 Token 有效期（秒）

    Args:
        token_type: access 或 refresh

    Returns:
        有效期秒数
    """
    if token_type == "refresh":
        return REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60


# ---- AES-256 加密/解密 ----

def _get_aes_key() -> bytes:
    """获取 AES-256 密钥（32字节）"""
    key = settings.AES_ENCRYPTION_KEY.encode("utf-8")
    # 使用 SHA-256 确保密钥长度为 32 字节
    return hashlib.sha256(key).digest()


def encrypt_sensitive(data: str) -> str:
    """AES-256-CBC 加密敏感数据

    Args:
        data: 明文数据

    Returns:
        Base64 编码的密文（格式：iv + ciphertext）
    """
    if not data:
        return data

    key = _get_aes_key()
    iv = os.urandom(16)  # 16字节随机 IV

    # PKCS7 填充
    padder = PKCS7(128).padder()
    padded_data = padder.update(data.encode("utf-8")) + padder.finalize()

    # AES-256-CBC 加密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # IV + 密文，Base64 编码
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_sensitive(encrypted_data: str) -> str:
    """AES-256-CBC 解密敏感数据

    Args:
        encrypted_data: Base64 编码的密文

    Returns:
        解密后的明文
    """
    if not encrypted_data:
        return encrypted_data

    key = _get_aes_key()
    raw = base64.b64decode(encrypted_data)

    # 分离 IV 和密文
    iv = raw[:16]
    ciphertext = raw[16:]

    # 解密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()

    # 去除 PKCS7 填充
    unpadder = PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data.decode("utf-8")


def hash_sensitive(data: str) -> str:
    """对敏感数据生成 SHA-256 哈希（用于查询索引）

    Args:
        data: 原始数据（如身份证号）

    Returns:
        哈希值（64位十六进制字符串）
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def mask_id_card(id_card: str) -> str:
    """身份证号脱敏：保留前4后4，中间用*

    Args:
        id_card: 身份证号

    Returns:
        脱敏后的身份证号，如 1101**********1234
    """
    if id_card and len(id_card) >= 8:
        return f"{id_card[:4]}{'*' * (len(id_card) - 8)}{id_card[-4:]}"
    return id_card
