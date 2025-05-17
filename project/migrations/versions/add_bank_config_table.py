"""
add bank_config table
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'bank_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bank_account', sa.String(length=128), nullable=False),
        sa.Column('fee', sa.Integer(), nullable=False, server_default='0'),
    )

def downgrade():
    op.drop_table('bank_config')
