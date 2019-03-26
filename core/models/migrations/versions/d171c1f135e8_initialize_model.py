"""initialize model

Revision ID: d171c1f135e8
Revises: 
Create Date: 2019-03-26 14:30:06.881439

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd171c1f135e8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('merchant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('descriptor', sa.String(length=256), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('executed_at', sa.Date(), nullable=False),
        sa.Column('merchant_id', sa.Integer()),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchant.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('transaction')
    op.drop_table('user')
    op.drop_table('merchant')
