"""add comment parent_id for replies

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('comments', sa.Column('parent_id', sa.Integer(), sa.ForeignKey('comments.id'), nullable=True))


def downgrade():
    op.drop_column('comments', 'parent_id')
