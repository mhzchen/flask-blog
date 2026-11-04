"""add github oauth columns on users

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    cols = [c['name'] for c in inspect(bind).get_columns('users')]
    if 'github_id' not in cols:
        op.add_column('users', sa.Column('github_id', sa.String(64), nullable=True))
        op.create_unique_constraint('uq_users_github_id', 'users', ['github_id'])
        op.add_column('users', sa.Column('github_username', sa.String(100), nullable=True))


def downgrade():
    bind = op.get_bind()
    cols = [c['name'] for c in inspect(bind).get_columns('users')]
    if 'github_id' in cols:
        op.drop_constraint('uq_users_github_id', 'users', type_='unique')
        op.drop_column('users', 'github_id')
        op.drop_column('users', 'github_username')
