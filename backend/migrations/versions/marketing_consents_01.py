"""Add marketing consent tables and note_marketing column

Revision ID: marketing_consents_01
Revises: patologie_coach_01
Create Date: 2026-04-02 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "marketing_consents_01"
down_revision = "patologie_coach_01"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Everything in raw SQL to avoid SQLAlchemy Enum auto-creation issues
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketingflagtypeenum') THEN
                CREATE TYPE marketingflagtypeenum AS ENUM (
                    'usabile_marketing','stories_editata','carosello_editato','videofeedback_editato'
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketingcontenttypeenum') THEN
                CREATE TYPE marketingcontenttypeenum AS ENUM (
                    'stories','carosello','videofeedback'
                );
            END IF;
        END $$;

        ALTER TABLE clienti ADD COLUMN IF NOT EXISTS note_marketing TEXT;
        ALTER TABLE clienti_version ADD COLUMN IF NOT EXISTS note_marketing TEXT;

        CREATE TABLE IF NOT EXISTS cliente_marketing_flags (
            id SERIAL PRIMARY KEY,
            cliente_id BIGINT NOT NULL REFERENCES clienti(cliente_id) ON DELETE CASCADE,
            flag_type marketingflagtypeenum NOT NULL,
            checked BOOLEAN NOT NULL DEFAULT false,
            checked_date DATE,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            CONSTRAINT uq_cliente_marketing_flags_cliente_tipo UNIQUE (cliente_id, flag_type)
        );

        CREATE INDEX IF NOT EXISTS ix_cliente_marketing_flags_cliente_id
            ON cliente_marketing_flags (cliente_id);

        CREATE TABLE IF NOT EXISTS cliente_marketing_content (
            id SERIAL PRIMARY KEY,
            cliente_id BIGINT NOT NULL REFERENCES clienti(cliente_id) ON DELETE CASCADE,
            content_type marketingcontenttypeenum NOT NULL,
            checked BOOLEAN NOT NULL DEFAULT false,
            checked_date DATE,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS ix_cliente_marketing_content_cliente_id
            ON cliente_marketing_content (cliente_id);
        CREATE INDEX IF NOT EXISTS ix_cliente_marketing_content_content_type
            ON cliente_marketing_content (content_type);

        CREATE TABLE IF NOT EXISTS cliente_marketing_influencers (
            id SERIAL PRIMARY KEY,
            marketing_content_id INTEGER NOT NULL REFERENCES cliente_marketing_content(id) ON DELETE CASCADE,
            influencer_id INTEGER NOT NULL REFERENCES influencers(influencer_id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            CONSTRAINT uq_marketing_content_influencer UNIQUE (marketing_content_id, influencer_id)
        );

        CREATE INDEX IF NOT EXISTS ix_cliente_marketing_influencers_content_id
            ON cliente_marketing_influencers (marketing_content_id);
        CREATE INDEX IF NOT EXISTS ix_cliente_marketing_influencers_influencer_id
            ON cliente_marketing_influencers (influencer_id);
    """))


def downgrade():
    op.execute("DROP TABLE IF EXISTS cliente_marketing_influencers")
    op.execute("DROP TABLE IF EXISTS cliente_marketing_content")
    op.execute("DROP TABLE IF EXISTS cliente_marketing_flags")
    op.execute("ALTER TABLE clienti DROP COLUMN IF EXISTS note_marketing")
    op.execute("DROP TYPE IF EXISTS marketingcontenttypeenum")
    op.execute("DROP TYPE IF EXISTS marketingflagtypeenum")
