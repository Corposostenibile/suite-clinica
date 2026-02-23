from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQL = BACKEND_DIR / "backups" / "migration_output_local" / "migrated_db_local.sql"
LOG_DIR = BACKEND_DIR / "backups" / "migration_output_local" / "logs"
PROGRESS_EVERY_SECONDS = 20


def load_database_url_from_env_file() -> str:
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env non trovato: {env_path}")
    for line in env_path.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL non trovato in backend/.env")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    log(f"[cmd] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def run_passthrough(cmd: list[str]) -> None:
    log(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"{ts()} {msg}", flush=True)


def fmt_seconds(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def ensure_enum_values(db_url: str) -> None:
    log("[step] enum fix: aggiungo valori legacy a statoclienteenum se mancanti")
    sqls = [
        "ALTER TYPE public.statoclienteenum ADD VALUE IF NOT EXISTS 'freeze';",
        "ALTER TYPE public.statoclienteenum ADD VALUE IF NOT EXISTS 'insoluto';",
    ]
    for sql in sqls:
        run_passthrough(["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql])


def import_sql(db_url: str, sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL migrato non trovato: {sql_path}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    err_log = LOG_DIR / f"import_cached_migrated_sql_{datetime.now().strftime('%Y%m%d_%H%M%S')}.stderr.log"
    log(f"[step] import: avvio psql su {sql_path}")
    log(f"[info] stderr psql -> {err_log}")
    cmd = ["psql", db_url, "-v", "ON_ERROR_STOP=0", "-f", str(sql_path)]
    log(f"[cmd] {' '.join(cmd)}")
    started = time.time()
    with err_log.open("w") as err_fh:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err_fh, text=True)
        while True:
            rc = proc.poll()
            if rc is not None:
                if rc != 0:
                    raise subprocess.CalledProcessError(rc, cmd)
                break
            elapsed = time.time() - started
            counts = read_counts_safe(db_url)
            err_size = err_log.stat().st_size if err_log.exists() else 0
            if counts:
                log(
                    "[progress] import in corso "
                    f"(elapsed={fmt_seconds(elapsed)}, pid={proc.pid}, "
                    f"users={counts['users']}, clienti={counts['clienti']}, "
                    f"push_subscriptions={counts['push_subscriptions']}, "
                    f"app_notifications={counts['app_notifications']}, "
                    f"stderr_kb={err_size // 1024})"
                )
            else:
                log(
                    "[progress] import in corso "
                    f"(elapsed={fmt_seconds(elapsed)}, pid={proc.pid}, stderr_kb={err_size // 1024})"
                )
            time.sleep(PROGRESS_EVERY_SECONDS)
    log(f"[step] import: completato in {fmt_seconds(time.time() - started)}")


def reset_dev_password() -> None:
    log("[step] post-import: reset password utente dev")
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
    log(f"[counts] users|clienti|push_subscriptions|app_notifications = {res.stdout.strip()}")


def read_counts_safe(db_url: str) -> dict[str, int] | None:
    sql = (
        "select "
        "(select count(*) from users),"
        "(select count(*) from clienti),"
        "(select count(*) from push_subscriptions),"
        "(select count(*) from app_notifications);"
    )
    try:
        res = subprocess.run(
            ["psql", db_url, "-At", "-F", "|", "-c", sql],
            check=True,
            text=True,
            capture_output=True,
        )
        values = [int(x) for x in res.stdout.strip().split("|")]
        if len(values) != 4:
            return None
        return {
            "users": values[0],
            "clienti": values[1],
            "push_subscriptions": values[2],
            "app_notifications": values[3],
        }
    except Exception:
        return None


def main() -> int:
    try:
        started = time.time()
        db_url = os.environ.get("DATABASE_URL") or load_database_url_from_env_file()
        sql_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SQL
        log("[start] import_cached_migrated_sql")
        log(f"[info] sql_path={sql_path}")
        ensure_enum_values(db_url)
        import_sql(db_url, sql_path)
        reset_dev_password()
        show_counts(db_url)
        log(f"[ok] Import cache SQL completato (durata totale={fmt_seconds(time.time() - started)})")
        return 0
    except subprocess.CalledProcessError as exc:
        print(exc.stdout or "", end="")
        print(exc.stderr or "", end="", file=sys.stderr)
        print(f"{ts()} [error] comando fallito (exit={exc.returncode}): {exc.cmd}", file=sys.stderr)
        return exc.returncode or 2
    except Exception as exc:
        print(f"{ts()} [error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
