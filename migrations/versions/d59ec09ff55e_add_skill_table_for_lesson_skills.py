"""add skill table for lesson skills

Revision ID: d59ec09ff55e
Revises: a94a9dc8d629
Create Date: 2025-12-02 02:59:25.652469

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd59ec09ff55e'
down_revision = 'a94a9dc8d629'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('skill',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('skill_text', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['lesson_id'], ['lesson.id'], name='skill_lesson_fk', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('skill')
