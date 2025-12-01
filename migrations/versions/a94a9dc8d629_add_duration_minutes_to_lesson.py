"""add duration_minutes to lesson

Revision ID: a94a9dc8d629
Revises: fc40fa00bc54
Create Date: 2025-12-02 02:34:22.522850

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a94a9dc8d629'
down_revision = 'fc40fa00bc54'
branch_labels = None
depends_on = None


def upgrade():
    # Add duration_minutes column to lesson table
    op.add_column('lesson', sa.Column('duration_minutes', sa.Integer(), nullable=True))


def downgrade():
    # Drop duration_minutes column
    op.drop_column('lesson', 'duration_minutes')
