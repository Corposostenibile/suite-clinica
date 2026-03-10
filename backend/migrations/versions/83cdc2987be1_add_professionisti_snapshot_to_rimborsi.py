"""add professionisti_snapshot to rimborsi

Revision ID: 83cdc2987be1
Revises: 500969977644
Create Date: 2026-03-09 00:35:35.269581

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '83cdc2987be1'
down_revision = '500969977644'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rimborsi', schema=None) as batch_op:
        batch_op.add_column(sa.Column('professionisti_snapshot', JSONB(), nullable=True))


def downgrade():
    with op.batch_alter_table('rimborsi', schema=None) as batch_op:
        batch_op.drop_column('professionisti_snapshot')
