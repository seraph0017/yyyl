"""
认证中间件 & FastAPI 依赖注入

- get_current_user：从 Token 获取当前用户
- get_current_active_user：确保用户状态正常
- require_role：角色权限校验
- get_optional_user：可选认证（游客可访问）
- get_current_admin：获取当前管理员
"""


from functools import wraps
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.admin import AdminUser
from models.user import User
from utils.security import verify_token

# OAuth2 scheme：从请求头 Authorization: Bearer {token} 提取 token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/admin/auth/login",
    auto_error=True,
)

# 可选认证：token 不存在时不报错
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/admin/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT Token 获取当前用户

    用于需要登录的接口。

    Args:
        token: JWT access_token
        db: 数据库会话

    Returns:
        User 模型实例

    Raises:
        HTTPException 40101: Token 过期或未登录
        HTTPException 40102: Token 无效
        HTTPException 40403: 用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": 40101, "message": "未登录或Token过期"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "Token无效"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证 token_type
    token_type = payload.get("token_type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "Token类型无效，请使用access_token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # admin token 的 sub 格式为 "admin:{id}"，不应进入用户认证流程
    if isinstance(user_id, str) and user_id.startswith("admin:"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "管理员Token不能用于C端接口，请使用用户Token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 查询用户
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == uid, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40403, "message": "用户不存在"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """确保当前用户状态正常（active）

    Args:
        current_user: 当前用户

    Returns:
        状态正常的 User 实例

    Raises:
        HTTPException 40301: 用户已被禁用或注销
    """
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": f"用户状态异常：{current_user.status}"},
        )
    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选认证：游客可访问，有 Token 则解析用户

    适用于商品列表等公开接口，有用户信息时可以提供个性化内容。

    Args:
        token: 可选的 JWT token
        db: 数据库会话

    Returns:
        User 实例或 None
    """
    if token is None:
        return None

    try:
        payload = verify_token(token)
        if payload.get("token_type") != "access":
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        # admin token 不解析为用户
        if isinstance(user_id, str) and user_id.startswith("admin:"):
            return None

        result = await db.execute(
            select(User).where(User.id == int(user_id), User.is_deleted.is_(False))
        )
        user = result.scalar_one_or_none()
        return user if user and user.status == "active" else None

    except (JWTError, ValueError):
        return None


def require_role(*roles: str) -> Callable:
    """角色权限校验装饰器

    支持的角色：user, staff, admin, super_admin

    角色继承关系（高角色包含低角色权限）：
    - super_admin > admin > staff > user

    用法：
    ```python
    @router.get("/admin/products")
    async def list_products(
        current_user: User = Depends(require_role("admin", "super_admin"))
    ):
        ...
    ```

    Args:
        *roles: 允许的角色列表

    Returns:
        FastAPI 依赖注入函数
    """
    allowed_roles = set(roles)

    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_role = current_user.role

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": 40301,
                    "message": f"权限不足，需要角色: {', '.join(allowed_roles)}",
                },
            )
        return current_user

    return role_checker


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """获取当前管理员用户

    用于管理后台接口，验证 admin_user 表中的记录。

    Args:
        token: JWT access_token
        db: 数据库会话

    Returns:
        AdminUser 模型实例

    Raises:
        HTTPException: Token 无效、管理员不存在、管理员被禁用
    """
    try:
        payload = verify_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "Token无效"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "Token类型无效"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 管理员 token 的 sub 格式为 "admin:{admin_id}"
    sub = payload.get("sub", "")
    role = payload.get("role", "")

    if role not in ("staff", "admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40302, "message": "需要管理员权限"},
        )

    # 解析 admin_id
    admin_id = sub.replace("admin:", "") if sub.startswith("admin:") else sub

    result = await db.execute(
        select(AdminUser).where(
            AdminUser.id == int(admin_id),
            AdminUser.is_deleted.is_(False),
        )
    )
    admin_user = result.scalar_one_or_none()

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 40403, "message": "管理员不存在"},
        )

    if admin_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": "管理员账号已被禁用"},
        )

    return admin_user


def require_admin_role(*roles: str) -> Callable:
    """管理员角色权限校验

    用法：
    ```python
    @router.post("/admin/products")
    async def create_product(
        admin: AdminUser = Depends(require_admin_role("admin", "super_admin"))
    ):
        ...
    ```
    """
    allowed_roles = set(roles)

    async def admin_role_checker(
        admin_user: AdminUser = Depends(get_current_admin),
    ) -> AdminUser:
        # 通过关联的 role 查看 role_code
        if admin_user.role and admin_user.role.role_code not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": 40301,
                    "message": f"权限不足，需要角色: {', '.join(allowed_roles)}",
                },
            )
        return admin_user

    return admin_role_checker


def require_permission(resource: str, action: str) -> Callable:
    """细粒度权限校验

    校验管理员是否拥有指定资源的操作权限。

    用法：
    ```python
    @router.post("/admin/products")
    async def create_product(
        admin: AdminUser = Depends(require_permission("product", "write"))
    ):
        ...
    ```
    """

    async def permission_checker(
        admin_user: AdminUser = Depends(get_current_admin),
    ) -> AdminUser:
        # super_admin 拥有所有权限
        if admin_user.role and admin_user.role.role_code == "super_admin":
            return admin_user

        # 检查权限表
        if admin_user.role and admin_user.role.permissions:
            for perm in admin_user.role.permissions:
                if perm.resource == resource and perm.action == action:
                    return admin_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": 40301,
                "message": f"权限不足：需要 {resource}:{action} 权限",
            },
        )

    return permission_checker
