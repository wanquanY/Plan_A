"""merge migration branches

Revision ID: 903a59e7596a
Revises: 1148ff29c074, b4a7bcbdbae3
Create Date: 2025-06-03 11:08:38.184519

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '903a59e7596a'
down_revision = ('1148ff29c074', 'b4a7bcbdbae3')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 