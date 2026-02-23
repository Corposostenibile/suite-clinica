from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQL = BACKEND_DIR / "backups" / "migration_output_local" / "migrated_db_local.sql"


def load_database_url_from_env_file() -> str:
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env non trovato: {env_path}")
    for line in env_path.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL non trovato in backend/.env")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"[cmd] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def run_passthrough(cmd: list[str]) -> None:
    print(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def ensure_enum_values(db_url: str) -> None:
    sqls = [
        "ALTER TYPE public.statoclienteenum ADD VALUE IF NOT EXISTS 'freeze';",
        "ALTER TYPE public.statoclienteenum ADD VALUE IF NOT EXISTS 'insoluto';",
    ]
    for sql in sqls:
        run_passthrough(["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql])


def import_sql(db_url: str, sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL migrato non trovato: {sql_path}")
    run_passthrough(["psql", db_url, "-v", "ON_ERROR_STOP=0", "-f", str(sql_path)])


def reset_dev_password() -> None:
    script = (
        "from corposostenibile import create_app;"
        "from corposostenibile.extensions import db;"
        "from corposostenibile.models import User;"
        "app=create_app();"
        "ctx=app.app_context();ctx.push();"
        "u=User.query.filter_by(email='dev@corposostenibile.it').first();"
        "print('dev_user_found=', bool(u));"
        "u and u.set_password('Dev123?');"
        "u and setattr(u,'is_active',True);"
        "u and setattr(u,'is_admin',True);"
        "u and db.session.commit();"
        "ctx.pop()"
    )
    run_passthrough(["poetry", "run", "python", "-c", script])


def show_counts(db_url: str) -> None:
    sql = (
        "select "
        "(select count(*) from users),"
        "(select count(*) from clienti),"
        "(select count(*) from push_subscriptions),"
        "(select count(*) from app_notifications);"
    )
    res = run(["psql", db_url, "-At", "-F", "|", "-c", sql])
    print(res.stdout.strip())


def main() -> int:
    try:
        db_url = os.environ.get("DATABASE_URL") or load_database_url_from_env_file()
        sql_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SQL
        ensure_enum_values(db_url)
        import_sql(db_url, sql_path)
        reset_dev_password()
        show_counts(db_url)
        print("[ok] Import cache SQL completato.")
        return 0
    except subprocess.CalledProcessError as exc:
        print(exc.stdout or "", end="")
        print(exc.stderr or "", end="", file=sys.stderr)
        print(f"[error] comando fallito (exit={exc.returncode}): {exc.cmd}", file=sys.stderr)
        return exc.returncode or 2
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
