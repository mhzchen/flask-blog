"""drop redundant indexes on posts

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def _has_index(index_name):
    """判断 posts 是否已有同名索引；按方言查询（MySQL 用 information_schema，SQLite 用 sqlite_master）。"""
    from sqlalchemy import text
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return bind.execute(
            text("SELECT COUNT(*) FROM sqlite_master "
                 "WHERE type='index' AND tbl_name='posts' AND name = :i"),
            {'i': index_name}
        ).scalar() > 0
    return bind.execute(
        text("SELECT COUNT(*) FROM information_schema.statistics "
             "WHERE table_schema = DATABASE() AND table_name = 'posts' AND index_name = :i"),
        {'i': index_name}
    ).scalar() > 0


def upgrade():
    """清理冗余索引：
    - ix_posts_content_fulltext：单列 content FULLTEXT，已被 ix_posts_search_fulltext（title+summary+content）覆盖；
    - ix_posts_title：单列普通索引，代码无 title 精确/前缀查询（LIKE %kw% 前导通配符用不到索引）。
    """
    if _has_index('ix_posts_content_fulltext'):
        op.drop_index('ix_posts_content_fulltext', table_name='posts')
    if _has_index('ix_posts_title'):
        op.drop_index('ix_posts_title', table_name='posts')


def downgrade():
    if op.get_bind().dialect.name == 'mysql' and not _has_index('ix_posts_content_fulltext'):
        op.execute("CREATE FULLTEXT INDEX ix_posts_content_fulltext ON posts (content)")
    if not _has_index('ix_posts_title'):
        op.create_index('ix_posts_title', 'posts', ['title'])