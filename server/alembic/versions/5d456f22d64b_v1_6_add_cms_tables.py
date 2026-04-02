"""v1.6 add CMS tables

Revision ID: 5d456f22d64b
Revises: a3b7c9d1e5f2
Create Date: 2026-04-01 09:08:24.730655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5d456f22d64b'
down_revision: Union[str, None] = 'a3b7c9d1e5f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CMS 组件注册表
    op.create_table('cms_component',
    sa.Column('site_id', sa.BigInteger(), server_default='1', nullable=False, comment='营地ID'),
    sa.Column('component_type', sa.String(length=32), nullable=False, comment='组件类型标识: banner/image/image_text/notice/nav/product_list/coupon/rich_text/spacer/divider/video'),
    sa.Column('name', sa.String(length=64), nullable=False, comment='组件显示名称'),
    sa.Column('icon', sa.String(length=128), nullable=True, comment='组件图标URL'),
    sa.Column('default_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='默认配置模板'),
    sa.Column('status', sa.String(length=16), server_default='active', nullable=False, comment='状态: active/inactive'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='软删除标记'),
    sa.PrimaryKeyConstraint('id'),
    comment='CMS 可用组件注册表'
    )
    op.create_index('idx_cms_comp_site_status', 'cms_component', ['site_id', 'status', 'sort_order'], unique=False)

    # CMS 页面主表
    op.create_table('cms_page',
    sa.Column('site_id', sa.BigInteger(), server_default='1', nullable=False, comment='营地ID'),
    sa.Column('page_code', sa.String(length=64), nullable=False, comment='页面标识，同一营地下唯一'),
    sa.Column('page_type', sa.String(length=32), nullable=False, comment='页面类型: home/activity/promotion/custom/landing'),
    sa.Column('title', sa.String(length=128), nullable=False, comment='页面标题'),
    sa.Column('description', sa.Text(), nullable=True, comment='页面描述'),
    sa.Column('status', sa.String(length=16), server_default='active', nullable=False, comment='页面状态: active/inactive'),
    sa.Column('current_version_id', sa.BigInteger(), nullable=True, comment='当前发布版本ID（逻辑引用，非FK，避免循环依赖）'),
    sa.Column('draft_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='草稿配置JSON'),
    sa.Column('draft_updated_at', sa.DateTime(timezone=True), nullable=True, comment='草稿最后更新时间（乐观锁）'),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False, comment='排序权重'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='软删除标记'),
    sa.PrimaryKeyConstraint('id'),
    comment='CMS 页面主表'
    )
    op.create_index('idx_cms_page_site_type', 'cms_page', ['site_id', 'page_type', 'status'], unique=False)
    op.create_index('uq_cms_page_site_code', 'cms_page', ['site_id', 'page_code'], unique=True, postgresql_where=sa.text('is_deleted = false'))

    # CMS 素材库
    op.create_table('cms_asset',
    sa.Column('site_id', sa.BigInteger(), server_default='1', nullable=False, comment='营地ID'),
    sa.Column('file_name', sa.String(length=256), nullable=False, comment='文件名（UUID重命名后）'),
    sa.Column('file_url', sa.String(length=512), nullable=False, comment='文件访问URL'),
    sa.Column('file_type', sa.String(length=32), nullable=False, comment='文件类型: image/video'),
    sa.Column('file_size', sa.Integer(), nullable=False, comment='文件大小（字节）'),
    sa.Column('width', sa.Integer(), nullable=True, comment='图片宽度（px）'),
    sa.Column('height', sa.Integer(), nullable=True, comment='图片高度（px）'),
    sa.Column('uploaded_by', sa.BigInteger(), nullable=False, comment='上传人ID'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='软删除标记'),
    sa.ForeignKeyConstraint(['uploaded_by'], ['admin_user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    comment='CMS 素材库'
    )
    op.create_index('idx_cms_asset_site', 'cms_asset', ['site_id', 'file_type'], unique=False)
    op.create_index('idx_cms_asset_uploaded_by', 'cms_asset', ['uploaded_by'], unique=False)

    # CMS 页面版本历史
    op.create_table('cms_page_version',
    sa.Column('page_id', sa.BigInteger(), nullable=False, comment='所属页面ID'),
    sa.Column('version_number', sa.Integer(), nullable=False, comment='版本序号'),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='页面配置JSON快照'),
    sa.Column('published_by', sa.BigInteger(), nullable=False, comment='发布人ID'),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False, comment='发布时间'),
    sa.Column('remark', sa.String(length=256), nullable=True, comment='发布备注'),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='软删除标记'),
    sa.ForeignKeyConstraint(['page_id'], ['cms_page.id'], ),
    sa.ForeignKeyConstraint(['published_by'], ['admin_user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    comment='CMS 页面版本历史'
    )
    op.create_index('idx_cms_pv_page', 'cms_page_version', ['page_id', 'version_number'], unique=False, postgresql_ops={'version_number': 'DESC'})
    op.create_index('idx_cms_pv_published_at', 'cms_page_version', ['published_at'], unique=False, postgresql_ops={'published_at': 'DESC'})


def downgrade() -> None:
    op.drop_index('idx_cms_pv_published_at', table_name='cms_page_version', postgresql_ops={'published_at': 'DESC'})
    op.drop_index('idx_cms_pv_page', table_name='cms_page_version', postgresql_ops={'version_number': 'DESC'})
    op.drop_table('cms_page_version')
    op.drop_index('idx_cms_asset_uploaded_by', table_name='cms_asset')
    op.drop_index('idx_cms_asset_site', table_name='cms_asset')
    op.drop_table('cms_asset')
    op.drop_index('uq_cms_page_site_code', table_name='cms_page', postgresql_where=sa.text('is_deleted = false'))
    op.drop_index('idx_cms_page_site_type', table_name='cms_page')
    op.drop_table('cms_page')
    op.drop_index('idx_cms_comp_site_status', table_name='cms_component')
    op.drop_table('cms_component')
