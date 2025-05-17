"""merge branches

Revision ID: e970c7dad4d6
Revises: 907bdd23a0b0, your_new_revision_id
Create Date: 2025-05-17 22:14:28.715619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e970c7dad4d6'
down_revision = ('907bdd23a0b0', 'your_new_revision_id')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
