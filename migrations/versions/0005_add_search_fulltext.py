"""fulltext search index on posts

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
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
    """为 title+summary+content 建组合 FULLTEXT 索引，带 ngram parser 以支持中文分词。

    注意：FULLTEXT 是 MySQL 专属能力，SQLite 不支持；
    为让同一迁移链在 SQLite（本地开发/CI）与 MySQL（生产）都能跑，
    仅当连接方言是 mysql 时才创建全文索引，SQLite 上跳过（不建该索引）。
    """
    bind = op.get_bind()
    if bind.dialect.name != 'mysql':
        return
    if not _has_index('ix_posts_search_fulltext'):
        op.execute(
            "CREATE FULLTEXT INDEX ix_posts_search_fulltext "
            "ON posts (title, summary, content) WITH PARSER ngram"
        )


def downgrade():
    op.drop_index('ix_posts_search_fulltext', table_name='posts')
