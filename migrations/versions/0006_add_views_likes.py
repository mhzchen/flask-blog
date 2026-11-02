"""add post views and post_likes table

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('posts', sa.Column('views', sa.Integer(), nullable=False, server_default='0'))
    op.create_table('post_likes',
                    sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
                    sa.Column('post_id', sa.Integer(), sa.ForeignKey('posts.id'), primary_key=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    )


def downgrade():
    op.drop_table('post_likes')
    op.drop_column('posts', 'views')
