from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from corposostenibile import create_app
from corposostenibile.extensions import db


def _repo_heads() -> list[str]:
    migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
    config = Config(str(migrations_dir / "alembic.ini"))
    config.set_main_option("script_location", str(migrations_dir))
    script = ScriptDirectory.from_config(config)
    return list(script.get_heads())


def main() -> int:
    heads = _repo_heads()
    print(f"[info] Repository heads: {heads}")

    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            current = [row[0] for row in conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()]
            print(f"[info] alembic_version before: {current}")

            conn.execute(text("DELETE FROM alembic_version"))
            for head in heads:
                conn.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
                    {"version_num": head},
                )

        with db.engine.connect() as conn:
            after = [row[0] for row in conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()]
        print(f"[ok] alembic_version after: {after}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
