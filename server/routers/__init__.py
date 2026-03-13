"""
API routers package

所有路由模块在此统一导出，便于 main.py 注册。
"""

from routers import (
    admin,
    auth,
    campsites,
    cart,
    content,
    finance,
    members,
    notifications,
    orders,
    products,
    reports,
    tickets,
    users,
)

__all__ = [
    "admin",
    "auth",
    "campsites",
    "cart",
    "content",
    "finance",
    "members",
    "notifications",
    "orders",
    "products",
    "reports",
    "tickets",
    "users",
]
