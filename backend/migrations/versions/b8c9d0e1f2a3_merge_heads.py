"""merge_heads

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2, 03cedd75f299, cb04_add_durata_clienti_ver
Create Date: 2026-02-27

Unifica i tre head delle migrazioni in un unico head.
"""
from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = ("a7b8c9d0e1f2", "03cedd75f299", "cb04_add_durata_clienti_ver")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
