"""Add assignment criteria and AI notes to User model

Revision ID: f3d4c5b6a7e8
Revises: e58532959213
Create Date: 2026-02-09 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f3d4c5b6a7e8'
down_revision = 'e58532959213'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('assignment_ai_notes', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Note strutturate per assegnazione automatica AI'))
    op.add_column('users', sa.Column('assignment_criteria', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Criteri booleani per matching programmatico'))

def downgrade():
    op.drop_column('users', 'assignment_criteria')
    op.drop_column('users', 'assignment_ai_notes')
