"""add missing indexes for performance optimization

Revision ID: perf_indexes_01
Revises: marketing_consents_01
Create Date: 2026-04-07 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "perf_indexes_01"
down_revision = "marketing_consents_01"
branch_labels = None
depends_on = None


def upgrade():
    # tasks.status — usato in quasi ogni query su /api/tasks/
    op.create_index("ix_tasks_status", "tasks", ["status"], if_not_exists=True)

    # tasks.category — usato in _build_stats() e filtri categoria
    op.create_index("ix_tasks_category", "tasks", ["category"], if_not_exists=True)

    # tasks.(assignee_id, status) — pattern comune: visibilità per assignee + filtro status
    op.create_index("ix_tasks_assignee_status", "tasks", ["assignee_id", "status"], if_not_exists=True)

    # tasks.(status, category) — usato da _build_stats() GROUP BY category WHERE status != done
    op.create_index("ix_tasks_status_category", "tasks", ["status", "category"], if_not_exists=True)

    # sales_leads.(source_system, converted_to_client_id) — query /old-suite/api/leads
    op.create_index(
        "ix_sales_leads_source_converted",
        "sales_leads",
        ["source_system", "converted_to_client_id"],
        if_not_exists=True,
    )

    # weekly_check_responses.(submit_date, weekly_check_id) — query range + join in azienda/stats
    op.create_index(
        "ix_weekly_check_responses_date_check",
        "weekly_check_responses",
        ["submit_date", "weekly_check_id"],
        if_not_exists=True,
    )

    # dca_check_responses.(submit_date, dca_check_id)
    op.create_index(
        "ix_dca_check_responses_date_check",
        "dca_check_responses",
        ["submit_date", "dca_check_id"],
        if_not_exists=True,
    )

    # minor_check_responses.(submit_date, minor_check_id)
    op.create_index(
        "ix_minor_check_responses_date_check",
        "minor_check_responses",
        ["submit_date", "minor_check_id"],
        if_not_exists=True,
    )


def downgrade():
    op.drop_index("ix_minor_check_responses_date_check", table_name="minor_check_responses", if_exists=True)
    op.drop_index("ix_dca_check_responses_date_check", table_name="dca_check_responses", if_exists=True)
    op.drop_index("ix_weekly_check_responses_date_check", table_name="weekly_check_responses", if_exists=True)
    op.drop_index("ix_sales_leads_source_converted", table_name="sales_leads", if_exists=True)
    op.drop_index("ix_tasks_status_category", table_name="tasks", if_exists=True)
    op.drop_index("ix_tasks_assignee_status", table_name="tasks", if_exists=True)
    op.drop_index("ix_tasks_category", table_name="tasks", if_exists=True)
    op.drop_index("ix_tasks_status", table_name="tasks", if_exists=True)
