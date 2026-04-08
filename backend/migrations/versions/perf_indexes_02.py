"""add missing indexes for slow endpoints

Revision ID: perf_indexes_02
Revises: perf_indexes_01
Create Date: 2026-04-08 09:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "perf_indexes_02"
down_revision = "dedafcfbe6df"
branch_labels = None
depends_on = None


def upgrade():
    # teams.is_active — usato in filtro /api/team/teams
    op.create_index("ix_teams_is_active", "teams", ["is_active"], if_not_exists=True)

    # typeform_responses.submit_date — usato in WHERE per azienda/stats
    op.create_index(
        "ix_typeform_responses_submit_date",
        "typeform_responses",
        ["submit_date"],
        if_not_exists=True,
    )

    # typeform_responses.typeform_id + submit_date — per query range
    op.create_index(
        "ix_typeform_responses_tf_date",
        "typeform_responses",
        ["typeform_id", "submit_date"],
        if_not_exists=True,
    )

    # typeform_responses.cliente_id — JOIN in azienda/stats
    try:
        op.create_index(
            "ix_typeform_responses_cliente_id",
            "typeform_responses",
            ["cliente_id"],
            if_not_exists=True,
        )
    except Exception:
        pass

    # dca_check.cliente_id — JOIN in azienda/stats
    op.create_index(
        "ix_dca_checks_cliente_id",
        "dca_checks",
        ["cliente_id"],
        if_not_exists=True,
    )

    # minor_checks.cliente_id — JOIN in azienda/stats
    op.create_index(
        "ix_minor_checks_cliente_id",
        "minor_checks",
        ["cliente_id"],
        if_not_exists=True,
    )

    # clienti — indici per join/filtri professionals/criteria e azienda/stats
    op.create_index("ix_clienti_nutrizionista_id", "clienti", ["nutrizionista_id"], if_not_exists=True)
    op.create_index("ix_clienti_coach_id", "clienti", ["coach_id"], if_not_exists=True)
    op.create_index("ix_clienti_psicologa_id", "clienti", ["psicologa_id"], if_not_exists=True)
    op.create_index("ix_clienti_health_manager_id", "clienti", ["health_manager_id"], if_not_exists=True)
    op.create_index("ix_clienti_consulente_alimentare_id", "clienti", ["consulente_alimentare_id"], if_not_exists=True)
    op.create_index("ix_clienti_stato_nutrizione", "clienti", ["stato_nutrizione"], if_not_exists=True)
    op.create_index("ix_clienti_stato_coach", "clienti", ["stato_coach"], if_not_exists=True)
    op.create_index("ix_clienti_stato_psicologia", "clienti", ["stato_psicologia"], if_not_exists=True)
    op.create_index("ix_clienti_stato_cliente", "clienti", ["stato_cliente"], if_not_exists=True)
    op.create_index("ix_clienti_service_status", "clienti", ["service_status"], if_not_exists=True)
    op.create_index("ix_users_specialty_active", "users", ["specialty", "is_active"], if_not_exists=True)


def downgrade():
    op.drop_index("ix_users_specialty_active", table_name="users", if_exists=True)
    op.drop_index("ix_clienti_service_status", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_stato_cliente", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_stato_psicologia", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_stato_coach", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_stato_nutrizione", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_consulente_alimentare_id", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_health_manager_id", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_psicologa_id", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_coach_id", table_name="clienti", if_exists=True)
    op.drop_index("ix_clienti_nutrizionista_id", table_name="clienti", if_exists=True)
    op.drop_index("ix_minor_checks_cliente_id", table_name="minor_checks", if_exists=True)
    op.drop_index("ix_dca_checks_cliente_id", table_name="dca_checks", if_exists=True)
    try:
        op.drop_index("ix_typeform_responses_cliente_id", table_name="typeform_responses", if_exists=True)
    except Exception:
        pass
    op.drop_index("ix_typeform_responses_tf_date", table_name="typeform_responses", if_exists=True)
    op.drop_index("ix_typeform_responses_submit_date", table_name="typeform_responses", if_exists=True)
    op.drop_index("ix_teams_is_active", table_name="teams", if_exists=True)
