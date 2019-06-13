"""nouvel index

Revision ID: b008dca695a6
Revises: d171c1f135e8
Create Date: 2019-06-12 14:05:05.211927

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b008dca695a6'
down_revision = 'd171c1f135e8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('index_user', 'transaction', ['id', 'user_id'])
    op.create_index('index_merchant', 'transaction', ['id', 'user_id'])


def downgrade():
    op.drop_index('index_user')
    op.drop_index('index_merchant')
