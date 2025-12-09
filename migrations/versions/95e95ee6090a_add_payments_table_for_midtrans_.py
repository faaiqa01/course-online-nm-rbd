"""Add payments table for Midtrans integration

Revision ID: 95e95ee6090a
Revises: 0a0205c6bed5
Create Date: 2025-12-02 09:53:36.381177

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95e95ee6090a'
down_revision = '0a0205c6bed5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.String(length=100), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('gross_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('payment_type', sa.String(length=50), nullable=True),
    sa.Column('transaction_status', sa.String(length=50), nullable=True),
    sa.Column('transaction_time', sa.DateTime(), nullable=True),
    sa.Column('settlement_time', sa.DateTime(), nullable=True),
    sa.Column('payment_data', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['course.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_id')
    )


def downgrade():
    op.drop_table('payments')
