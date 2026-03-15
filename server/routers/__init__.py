"""
API routers package

所有路由模块在此统一导出，便于 main.py 注册。
"""

from routers import (
    admin,
    auth,
    bundles,
    camp_maps,
    campsites,
    cart,
    content,
    expenses,
    finance,
    members,
    notifications,
    orders,
    performance,
    products,
    reports,
    seckill,
    tickets,
    users,
    weather,
)

__all__ = [
    "admin",
    "auth",
    "bundles",
    "camp_maps",
    "campsites",
    "cart",
    "content",
    "expenses",
    "finance",
    "members",
    "notifications",
    "orders",
    "performance",
    "products",
    "reports",
    "seckill",
    "tickets",
    "users",
    "weather",
]
