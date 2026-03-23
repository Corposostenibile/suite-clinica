from corposostenibile import create_app
from corposostenibile.extensions import db
from sqlalchemy import text


SQL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS video_review_requests (
      id SERIAL PRIMARY KEY,
      cliente_id BIGINT NOT NULL REFERENCES clienti(cliente_id),
      requested_by_user_id INTEGER NOT NULL REFERENCES users(id),
      hm_user_id INTEGER REFERENCES users(id),
      status VARCHAR(32) NOT NULL,
      booking_confirmed_at TIMESTAMP NOT NULL,
      hm_confirmed_at TIMESTAMP,
      loom_link VARCHAR(500),
      hm_note TEXT,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_video_review_requests_cliente_id ON video_review_requests (cliente_id)",
    "CREATE INDEX IF NOT EXISTS ix_video_review_requests_hm_user_id ON video_review_requests (hm_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_video_review_requests_requested_by_user_id ON video_review_requests (requested_by_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_video_review_requests_status ON video_review_requests (status)",
    "ALTER TABLE clienti ADD COLUMN IF NOT EXISTS note_marketing TEXT",
    "ALTER TABLE clienti_version ADD COLUMN IF NOT EXISTS note_marketing TEXT",
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'marketingflagtypeenum' AND n.nspname = 'public'
      ) THEN
        CREATE TYPE public.marketingflagtypeenum AS ENUM (
          'usabile_marketing',
          'stories_editata',
          'carosello_editato',
          'videofeedback_editato'
        );
      END IF;
    END
    $$;
    """,
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'marketingcontenttypeenum' AND n.nspname = 'public'
      ) THEN
        CREATE TYPE public.marketingcontenttypeenum AS ENUM (
          'stories',
          'carosello',
          'videofeedback'
        );
      END IF;
    END
    $$;
    """,
    """
    CREATE TABLE IF NOT EXISTS cliente_marketing_flags (
      id SERIAL PRIMARY KEY,
      cliente_id BIGINT NOT NULL REFERENCES clienti(cliente_id) ON DELETE CASCADE,
      flag_type public.marketingflagtypeenum NOT NULL,
      checked BOOLEAN NOT NULL DEFAULT false,
      checked_date DATE,
      created_at TIMESTAMP,
      updated_at TIMESTAMP,
      CONSTRAINT uq_cliente_marketing_flags_cliente_tipo UNIQUE (cliente_id, flag_type)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_cliente_marketing_flags_cliente_id ON cliente_marketing_flags (cliente_id)",
    """
    CREATE TABLE IF NOT EXISTS cliente_marketing_content (
      id SERIAL PRIMARY KEY,
      cliente_id BIGINT NOT NULL REFERENCES clienti(cliente_id) ON DELETE CASCADE,
      content_type public.marketingcontenttypeenum NOT NULL,
      checked BOOLEAN NOT NULL DEFAULT false,
      checked_date DATE,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_cliente_marketing_content_cliente_id ON cliente_marketing_content (cliente_id)",
    "CREATE INDEX IF NOT EXISTS ix_cliente_marketing_content_content_type ON cliente_marketing_content (content_type)",
    """
    CREATE TABLE IF NOT EXISTS cliente_marketing_influencers (
      id SERIAL PRIMARY KEY,
      marketing_content_id INTEGER NOT NULL REFERENCES cliente_marketing_content(id) ON DELETE CASCADE,
      influencer_id INTEGER NOT NULL REFERENCES influencers(influencer_id) ON DELETE CASCADE,
      created_at TIMESTAMP,
      updated_at TIMESTAMP,
      CONSTRAINT uq_marketing_content_influencer UNIQUE (marketing_content_id, influencer_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_cliente_marketing_influencers_content_id ON cliente_marketing_influencers (marketing_content_id)",
    "CREATE INDEX IF NOT EXISTS ix_cliente_marketing_influencers_influencer_id ON cliente_marketing_influencers (influencer_id)",
]


def main() -> None:
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in SQL_STATEMENTS:
                conn.execute(text(stmt))
    print("OK: marketing consents schema ensured")


if __name__ == "__main__":
    main()
