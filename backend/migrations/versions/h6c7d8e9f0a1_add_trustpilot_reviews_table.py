"""add trustpilot_reviews table with API fields

Revision ID: trustpilot_reviews_01
Revises: onboarding_loom_fields_01
Create Date: 2026-03-18 12:00:00.000000

"""
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'trustpilot_reviews_01'
down_revision = 'onboarding_loom_fields_01'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    exists = conn.execute(text("SELECT to_regclass('public.trustpilot_reviews')")).scalar()

    if exists is None:
        op.execute("""
            CREATE TABLE trustpilot_reviews (
                id SERIAL PRIMARY KEY,
                cliente_id BIGINT NOT NULL REFERENCES clienti(cliente_id),
                richiesta_da_professionista_id INTEGER NOT NULL REFERENCES users(id),
                data_richiesta TIMESTAMP NOT NULL,
                invitation_method VARCHAR(50),
                invitation_status VARCHAR(50),
                trustpilot_reference_id VARCHAR(120) UNIQUE,
                trustpilot_invitation_id VARCHAR(120),
                trustpilot_review_id VARCHAR(120) UNIQUE,
                trustpilot_link TEXT,
                pubblicata BOOLEAN,
                data_pubblicazione TIMESTAMP,
                stelle INTEGER,
                testo_recensione TEXT,
                titolo_recensione VARCHAR(255),
                deleted_at_trustpilot TIMESTAMP,
                webhook_received_at TIMESTAMP,
                trustpilot_payload_last JSON,
                bonus_distribution JSON,
                applied_to_quarter VARCHAR(10),
                applied_to_week_start DATE,
                confermata_da_hm_id INTEGER REFERENCES users(id),
                data_conferma_hm TIMESTAMP,
                note_interne TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
    else:
        # Table exists from earlier migration — add API columns
        for col_sql in [
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS invitation_method VARCHAR(50)",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS invitation_status VARCHAR(50)",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS trustpilot_reference_id VARCHAR(120) UNIQUE",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS trustpilot_invitation_id VARCHAR(120)",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS trustpilot_review_id VARCHAR(120) UNIQUE",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS trustpilot_link TEXT",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS titolo_recensione VARCHAR(255)",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS deleted_at_trustpilot TIMESTAMP",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS webhook_received_at TIMESTAMP",
            "ALTER TABLE trustpilot_reviews ADD COLUMN IF NOT EXISTS trustpilot_payload_last JSON",
        ]:
            op.execute(col_sql)

    op.execute("CREATE INDEX IF NOT EXISTS idx_cliente_review ON trustpilot_reviews (cliente_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_richiedente ON trustpilot_reviews (richiesta_da_professionista_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_quarter ON trustpilot_reviews (applied_to_quarter)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pubblicata ON trustpilot_reviews (pubblicata)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_trustpilot_reference ON trustpilot_reviews (trustpilot_reference_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_trustpilot_review_id ON trustpilot_reviews (trustpilot_review_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS trustpilot_reviews CASCADE")
