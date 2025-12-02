"""add passing_grade and attempt_limit to course

Revision ID: 0a0205c6bed5
Revises: d59ec09ff55e
Create Date: 2025-12-02 03:20:40.029345

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a0205c6bed5'
down_revision = 'd59ec09ff55e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course', sa.Column('passing_grade', sa.Integer(), nullable=True, server_default='100'))
    op.add_column('course', sa.Column('attempt_limit', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('course', 'attempt_limit')
    op.drop_column('course', 'passing_grade')
