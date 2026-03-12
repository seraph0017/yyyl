"""
中间件包

认证 & 权限校验依赖注入。
"""

from middleware.auth import (  # noqa: F401
    get_current_active_user,
    get_current_admin,
    get_current_user,
    get_optional_user,
    require_admin_role,
    require_permission,
    require_role,
)
