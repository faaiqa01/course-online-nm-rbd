"""add learning_outcome table

Revision ID: 97ecdb58a130
Revises: bedc8996fae0
Create Date: 2025-12-02 01:51:08.611618

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '97ecdb58a130'
down_revision = 'bedc8996fae0'
branch_labels = None
depends_on = None


def upgrade():
    # Create learning_outcome table
    op.create_table('learning_outcome',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('outcome_text', sa.String(length=500), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop learning_outcome table
    op.drop_table('learning_outcome')
