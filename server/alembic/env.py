"""
Alembic 迁移环境配置
支持异步 PostgreSQL 连接（asyncpg）
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 将 server/ 目录加入 sys.path，以便导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402

# 导入所有模型（确保元数据完整）
from models import Base  # noqa: E402

# Alembic Config 对象
config = context.config

# 动态设置数据库 URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据（用于 autogenerate）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式迁移（仅生成 SQL 脚本，不连接数据库）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在给定连接上执行迁移"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步在线模式迁移"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式迁移（异步引擎）"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
