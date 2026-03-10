"""add rimborsi table and data_fine_percorso to clienti

Revision ID: 500969977644
Revises: cb05_influencer_origins_m2m
Create Date: 2026-03-09 00:01:29.110632

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '500969977644'
down_revision = 'cb05_influencer_origins_m2m'
branch_labels = None
depends_on = None


def upgrade():
    # Tabella rimborsi
    op.create_table('rimborsi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.BigInteger(), nullable=False),
        sa.Column('tipologia', sa.String(length=30), nullable=False),
        sa.Column('motivato', sa.Boolean(), nullable=False),
        sa.Column('motivazione', sa.Text(), nullable=True),
        sa.Column('data_fine_percorso', sa.Date(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['clienti.cliente_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rimborsi', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rimborsi_cliente_id'), ['cliente_id'], unique=False)

    # Aggiunta colonna data_fine_percorso a clienti
    with op.batch_alter_table('clienti', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_fine_percorso', sa.Date(), nullable=True))

    # Aggiunta colonna data_fine_percorso a clienti_version (versioning)
    with op.batch_alter_table('clienti_version', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_fine_percorso', sa.Date(), autoincrement=False, nullable=True))


def downgrade():
    with op.batch_alter_table('clienti_version', schema=None) as batch_op:
        batch_op.drop_column('data_fine_percorso')

    with op.batch_alter_table('clienti', schema=None) as batch_op:
        batch_op.drop_column('data_fine_percorso')

    with op.batch_alter_table('rimborsi', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rimborsi_cliente_id'))

    op.drop_table('rimborsi')
