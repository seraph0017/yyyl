"""
营地隔离中间件
从请求头 X-Site-Id 中获取当前营地ID，用于数据隔离
"""

from __future__ import annotations

from fastapi import Request


def get_site_id(request: Request) -> int:
    """
    从请求头中获取 site_id
    
    前端每个请求都会带上 X-Site-Id 头:
    - 西郊林场: 1
    - 大聋谷: 2
    
    默认返回 1（西郊林场）
    """
    site_id_str = request.headers.get("X-Site-Id", "1")
    try:
        site_id = int(site_id_str)
        # 验证 site_id 合法性
        if site_id not in (1, 2):
            return 1
        return site_id
    except (ValueError, TypeError):
        return 1
