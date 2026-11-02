"""add search/query indexes to posts

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def _has_index(index_name):
    """MySQL 无 CREATE INDEX IF NOT EXISTS，通过 information_schema 判断索引是否已存在，保证迁移可重复执行。"""
    from sqlalchemy import text
    bind = op.get_bind()
    return bind.execute(
        text("SELECT COUNT(*) FROM information_schema.statistics "
             "WHERE table_schema = DATABASE() AND table_name = 'posts' AND index_name = :i"),
        {'i': index_name}
    ).scalar() > 0


def upgrade():
    """为常用查询列建普通索引；为正文建 MySQL FULLTEXT 索引（原生 SQL，服务后续全文搜索）。"""
    if not _has_index('ix_posts_title'):
        op.create_index('ix_posts_title', 'posts', ['title'])
    if not _has_index('ix_posts_category_id'):
        op.create_index('ix_posts_category_id', 'posts', ['category_id'])
    if not _has_index('ix_posts_created_at'):
        op.create_index('ix_posts_created_at', 'posts', ['created_at'])
    if not _has_index('ix_posts_content_fulltext'):
        op.execute("CREATE FULLTEXT INDEX ix_posts_content_fulltext ON posts (content)")


def downgrade():
    op.drop_index('ix_posts_content_fulltext', table_name='posts')
    op.drop_index('ix_posts_created_at', table_name='posts')
    op.drop_index('ix_posts_category_id', table_name='posts')
    op.drop_index('ix_posts_title', table_name='posts')
