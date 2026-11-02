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
    # batch_alter_table：SQLite 用 copy-and-move 重建表（支持 ALTER 加约束列），MySQL 走原生 ALTER；
    # 让 dev(SQLite)/prod(MySQL) 都能跑完整迁移链
    with op.batch_alter_table('comments') as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), sa.ForeignKey('comments.id', name='fk_comments_parent'), nullable=True))


def downgrade():
    with op.batch_alter_table('comments') as batch_op:
        batch_op.drop_column('parent_id')
