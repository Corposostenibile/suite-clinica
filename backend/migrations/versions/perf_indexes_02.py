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

    # typeform_response.cliente_id — JOIN in azienda/stats
    # (tabella potrebbe essere typeform_response o typeform_responses)
    # Proviamo con typeform_responses (nome corretto da inspect)
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


def downgrade():
    op.drop_index("ix_minor_checks_cliente_id", table_name="minor_checks", if_exists=True)
    op.drop_index("ix_dca_checks_cliente_id", table_name="dca_checks", if_exists=True)
    try:
        op.drop_index("ix_typeform_responses_cliente_id", table_name="typeform_responses", if_exists=True)
    except Exception:
        pass
    op.drop_index("ix_typeform_responses_tf_date", table_name="typeform_responses", if_exists=True)
    op.drop_index("ix_typeform_responses_submit_date", table_name="typeform_responses", if_exists=True)
    op.drop_index("ix_teams_is_active", table_name="teams", if_exists=True)
