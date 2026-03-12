"""initial_schema_45_tables

Revision ID: 078ed7222391
Revises:
Create Date: 2026-03-12 00:20:55.350276

"""

from typing import Sequence, Union

from alembic import op

import sys
from pathlib import Path

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models import Base  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = "078ed7222391"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建所有45张数据表"""
    # 使用 SQLAlchemy 元数据，按依赖顺序创建全部表
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """删除所有45张数据表"""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
