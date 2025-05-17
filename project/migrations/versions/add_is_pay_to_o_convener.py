"""Add is_pay field to OConvener"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'your_new_revision_id'  # <- Alembic 会自动填入的，你不用改
down_revision = 'b80efc5dfbd7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('o_convener', sa.Column('is_pay', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('o_convener', 'is_pay')
