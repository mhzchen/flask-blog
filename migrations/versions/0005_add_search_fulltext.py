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
    from sqlalchemy import text
    bind = op.get_bind()
    return bind.execute(
        text("SELECT COUNT(*) FROM information_schema.statistics "
             "WHERE table_schema = DATABASE() AND table_name = 'posts' AND index_name = :i"),
        {'i': index_name}
    ).scalar() > 0


def upgrade():
    """为 title+summary+content 建组合 FULLTEXT 索引，带 ngram parser 以支持中文分词。"""
    if not _has_index('ix_posts_search_fulltext'):
        op.execute(
            "CREATE FULLTEXT INDEX ix_posts_search_fulltext "
            "ON posts (title, summary, content) WITH PARSER ngram"
        )


def downgrade():
    op.drop_index('ix_posts_search_fulltext', table_name='posts')
