"""change learning_outcome from course_id to lesson_id

Revision ID: fc40fa00bc54
Revises: 97ecdb58a130
Create Date: 2025-12-02 02:10:51.537243

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc40fa00bc54'
down_revision = '97ecdb58a130'
branch_labels = None
depends_on = None


def upgrade():
    # Check and add foreign key if not exists
    op.create_foreign_key('learning_outcome_lesson_fk', 'learning_outcome', 'lesson', ['lesson_id'], ['id'], ondelete='CASCADE')


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('learning_outcome_lesson_fk', 'learning_outcome', type_='foreignkey')
