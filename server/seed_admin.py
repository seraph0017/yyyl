"""
创建初始管理员账号的种子脚本

用法:
    cd server
    python seed_admin.py
"""

import asyncio
import sys

from sqlalchemy import text

from database import async_session_factory, engine
from utils.security import hash_password


# ---- 测试账号配置 ----
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "admin123456"
TEST_ADMIN_REAL_NAME = "超级管理员"
TEST_ADMIN_PHONE = "13800000000"

# 所有资源和操作的组合
RESOURCES = [
    "product", "order", "member", "finance", "inventory",
    "ticket", "dashboard", "system", "faq", "notification",
    "times_card", "page_config", "operation_log",
]
ACTIONS = ["read", "write", "delete", "export"]


async def seed():
    async with async_session_factory() as session:
        try:
            # 1. 检查/创建 super_admin 角色
            result = await session.execute(
                text("SELECT id FROM admin_role WHERE role_code = :code"),
                {"code": "super_admin"},
            )
            row = result.fetchone()

            if row is None:
                result = await session.execute(
                    text("""
                        INSERT INTO admin_role (role_name, role_code, description, site_id)
                        VALUES (:name, :code, :desc, 1)
                        RETURNING id
                    """),
                    {
                        "name": "超级管理员",
                        "code": "super_admin",
                        "desc": "拥有所有权限的超级管理员",
                    },
                )
                role_id = result.scalar_one()
                print(f"✅ 创建角色: 超级管理员 (id={role_id})")

                # 赋予所有权限
                count = 0
                for resource in RESOURCES:
                    for action in ACTIONS:
                        await session.execute(
                            text("""
                                INSERT INTO admin_permission (role_id, resource, action)
                                VALUES (:role_id, :resource, :action)
                            """),
                            {"role_id": role_id, "resource": resource, "action": action},
                        )
                        count += 1
                print(f"✅ 已赋予 {count} 项权限")
            else:
                role_id = row[0]
                print(f"ℹ️  角色已存在: 超级管理员 (id={role_id})")

            # 2. 检查/创建管理员账号
            result = await session.execute(
                text("SELECT id FROM admin_user WHERE username = :username"),
                {"username": TEST_ADMIN_USERNAME},
            )
            row = result.fetchone()

            pw_hash = hash_password(TEST_ADMIN_PASSWORD)

            if row is None:
                result = await session.execute(
                    text("""
                        INSERT INTO admin_user
                            (username, password_hash, real_name, phone, role_id, status, site_id)
                        VALUES
                            (:username, :pw, :name, :phone, :role_id, 'active', 1)
                        RETURNING id
                    """),
                    {
                        "username": TEST_ADMIN_USERNAME,
                        "pw": pw_hash,
                        "name": TEST_ADMIN_REAL_NAME,
                        "phone": TEST_ADMIN_PHONE,
                        "role_id": role_id,
                    },
                )
                admin_id = result.scalar_one()
                print(f"✅ 创建管理员: {TEST_ADMIN_USERNAME} (id={admin_id})")
            else:
                admin_id = row[0]
                await session.execute(
                    text("""
                        UPDATE admin_user
                        SET password_hash = :pw, role_id = :role_id, status = 'active'
                        WHERE id = :id
                    """),
                    {"pw": pw_hash, "role_id": role_id, "id": admin_id},
                )
                print(f"ℹ️  管理员已存在，已重置密码: {TEST_ADMIN_USERNAME} (id={admin_id})")

            await session.commit()

            print("\n" + "=" * 40)
            print("🎉 测试管理员账号信息:")
            print(f"   用户名: {TEST_ADMIN_USERNAME}")
            print(f"   密码:   {TEST_ADMIN_PASSWORD}")
            print(f"   角色:   超级管理员 (super_admin)")
            print("=" * 40)

        except Exception as e:
            await session.rollback()
            print(f"❌ 错误: {e}", file=sys.stderr)
            raise
        finally:
            await session.close()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
