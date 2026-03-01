"""sync team heads to team_leader role

Revision ID: 90f0ea3788d9
Revises: e6f7a8b9c0d1
Create Date: 2026-02-25 18:02:00.569166

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90f0ea3788d9'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    # Data migration: allinea i ruoli agli head dei team.
    # Promuove a team_leader gli utenti non-admin che risultano head di almeno un team.
    # Evita di toccare ruoli speciali (admin/influencer/health_manager) se già impostati.
    op.execute(
        sa.text(
            """
            UPDATE users u
            SET role = 'team_leader'
            WHERE COALESCE(u.is_admin, FALSE) = FALSE
              AND EXISTS (
                SELECT 1
                FROM teams t
                WHERE t.head_id = u.id
                  AND COALESCE(t.is_active, TRUE) = TRUE
              )
              AND (
                u.role IS NULL
                OR u.role IN ('professionista', 'team_esterno')
              )
            """
        )
    )


def downgrade():
    # No-op: non possiamo sapere con certezza quali utenti erano professionisti prima della sync.
    pass
