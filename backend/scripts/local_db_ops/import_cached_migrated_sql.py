from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQL = BACKEND_DIR / "backups" / "migration_output_local" / "migrated_db_local.sql"
TABLES_DIR = BACKEND_DIR / "backups" / "migration_output_local" / "tables"
ORDER_FILE = TABLES_DIR / "order.tsv"
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


def fmt_pct(num: int, den: int) -> str:
    if den <= 0:
        return "100.00"
    return f"{(num / den) * 100:.2f}"


def ensure_enum_values(db_url: str) -> None:
    log("[step] enum fix: aggiungo valori legacy a statoclienteenum se mancanti")
    sqls = [
        "ALTER TYPE public.statoclienteenum ADD VALUE IF NOT EXISTS 'freeze';",
        "ALTER TYPE public.statoclienteenum ADD VALUE IF NOT EXISTS 'insoluto';",
    ]
    for sql in sqls:
        run_passthrough(["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql])


# Allineato a backend/scripts/migration_scripts/schema_comparator.py (ENUM_ALIASES['statoclienteenum'])
STATO_CLIENTE_ENUM_ALIASES = {
    "freeze": "pausa",
    "insoluto": "stop",
}


def normalize_legacy_statoclienteenum_values(db_url: str) -> None:
    """
    Normalizza i valori legacy del tipo enum public.statoclienteenum su tutte le colonne
    che usano quel tipo, replicando la stessa mappa alias usata dallo script di migrazione
    produzione (schema_comparator.py).
    """
    log("[step] post-import: normalizzazione alias legacy per public.statoclienteenum")
    list_cols_sql = """
    SELECT table_schema, table_name, column_name
    FROM information_schema.columns
    WHERE udt_schema = 'public'
      AND udt_name = 'statoclienteenum'
    ORDER BY table_schema, table_name, ordinal_position;
    """
    res = run(["psql", db_url, "-At", "-F", "|", "-c", list_cols_sql])
    rows = [line.split("|", 2) for line in res.stdout.strip().splitlines() if line.strip()]
    if not rows:
        log("[info] nessuna colonna con tipo public.statoclienteenum trovata")
        return

    total_updates = 0
    for schema_name, table_name, column_name in rows:
        for old_val, new_val in STATO_CLIENTE_ENUM_ALIASES.items():
            sql = f"""
            UPDATE "{schema_name}"."{table_name}"
            SET "{column_name}" = '{new_val}'
            WHERE "{column_name}"::text = '{old_val}';
            """
            upd = run(["psql", db_url, "-At", "-F", "|", "-c", sql])
            # psql prints e.g. "UPDATE 13"
            out = (upd.stdout or "").strip()
            if out.startswith("UPDATE "):
                try:
                    changed = int(out.split()[1])
                except Exception:
                    changed = 0
                if changed:
                    total_updates += changed
                    log(
                        "[enum-normalize] "
                        f"{schema_name}.{table_name}.{column_name}: "
                        f"{old_val} -> {new_val} ({changed})"
                    )
    log(f"[step] post-import: normalizzazione statoclienteenum completata (rows={total_updates})")


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
            try:
                proc.wait(timeout=PROGRESS_EVERY_SECONDS)
            except subprocess.TimeoutExpired:
                pass
    log(f"[step] import: completato in {fmt_seconds(time.time() - started)}")


def parse_order_file(order_path: Path) -> list[dict[str, object]]:
    if not order_path.exists():
        raise FileNotFoundError(f"order.tsv non trovato: {order_path}")
    rows: list[dict[str, object]] = []
    with order_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.rstrip("\n")
            if not line:
                continue
            if i == 0 and line.startswith("idx\t"):
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                raise RuntimeError(f"Riga order.tsv non valida ({i+1}): {line}")
            idx_s, table, source_s, file_s = parts
            rows.append(
                {
                    "idx": int(idx_s),
                    "table": table,
                    "source_rows": int(source_s),
                    "file": Path(file_s),
                }
            )
    if not rows:
        raise RuntimeError(f"Nessuna tabella in {order_path}")
    return rows


def psql_scalar(db_url: str, sql: str) -> str:
    res = run(["psql", db_url, "-At", "-F", "|", "-c", sql])
    return res.stdout.strip()


def get_table_count(db_url: str, table: str) -> int:
    try:
        out = psql_scalar(db_url, f'SELECT count(*) FROM public."{table}";')
        return int(out or "0")
    except Exception:
        return 0


def truncate_replay_tables(db_url: str, order_rows: list[dict[str, object]]) -> None:
    table_sql = ", ".join(f'public."{r["table"]}"' for r in order_rows)
    log(f"[step] truncate: {len(order_rows)} tabelle (CASCADE)")
    run_passthrough(["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", f"TRUNCATE TABLE {table_sql} CASCADE;"])


def import_split_tables(db_url: str, order_path: Path = ORDER_FILE) -> None:
    order_rows = parse_order_file(order_path)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    err_log = LOG_DIR / f"import_cached_migrated_sql_{datetime.now().strftime('%Y%m%d_%H%M%S')}.stderr.log"
    total_tables = len(order_rows)
    total_source = sum(int(r["source_rows"]) for r in order_rows)
    total_target = 0
    started = time.time()
    log(f"[step] import(split): replay da {order_path}")
    log(f"[info] tables_dir={TABLES_DIR}")
    log(f"[info] stderr psql -> {err_log}")
    truncate_replay_tables(db_url, order_rows)

    with err_log.open("w") as err_fh:
        for step, row in enumerate(order_rows, start=1):
            table = str(row["table"])
            source_rows = int(row["source_rows"])
            sql_file = Path(str(row["file"]))
            if not sql_file.exists():
                raise FileNotFoundError(f"File SQL tabella non trovato: {sql_file}")

            table_started = time.time()
            cmd = ["psql", db_url, "-q", "-v", "ON_ERROR_STOP=1", "-f", str(sql_file)]
            log(f"[cmd] {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err_fh, text=True)
            while True:
                rc = proc.poll()
                if rc is not None:
                    if rc != 0:
                        raise subprocess.CalledProcessError(rc, cmd)
                    break
                elapsed = time.time() - started
                table_elapsed = time.time() - table_started
                target_now = get_table_count(db_url, table)
                err_size = err_log.stat().st_size if err_log.exists() else 0
                log(
                    "[migration][progress] "
                    f"table={table} step={step}/{total_tables} "
                    f"source={source_rows} target={target_now} "
                    f"table_pct={fmt_pct(target_now, source_rows)} "
                    f"total_target={total_target + target_now} total_source={total_source} "
                    f"total_pct={fmt_pct(total_target + target_now, total_source)} "
                    f"elapsed={fmt_seconds(elapsed)} table_elapsed={fmt_seconds(table_elapsed)} "
                    f"pid={proc.pid} stderr_kb={(err_size // 1024)}"
                )
                try:
                    proc.wait(timeout=PROGRESS_EVERY_SECONDS)
                except subprocess.TimeoutExpired:
                    pass

            target_rows = get_table_count(db_url, table)
            total_target += target_rows
            log(
                "[migration][done] "
                f"table={table} step={step}/{total_tables} "
                f"source={source_rows} target={target_rows} "
                f"table_pct={fmt_pct(target_rows, source_rows)} "
                f"total_target={total_target} total_source={total_source} "
                f"total_pct={fmt_pct(total_target, total_source)} "
                f"table_time={fmt_seconds(time.time() - table_started)}"
            )

    log(f"[step] import(split): completato in {fmt_seconds(time.time() - started)}")


def reset_dev_password() -> None:
    log("[step] post-import: ensure/reset utente dev")
    script = (
        "from corposostenibile import create_app;"
        "from corposostenibile.extensions import db;"
        "from corposostenibile.models import User,UserRoleEnum;"
        "app=create_app();"
        "ctx=app.app_context();ctx.push();"
        "u=User.query.filter_by(email='dev@corposostenibile.it').first();"
        "created=False;"
        "import builtins;"
        "u = u or User(email='dev@corposostenibile.it', first_name='Dev', last_name='Admin');"
        "created = (u.id is None);"
        "created and db.session.add(u);"
        "u.set_password('Dev123?');"
        "u.is_active=True;"
        "u.is_admin=True;"
        "u.is_external=False;"
        "u.is_trial=False;"
        "u.role=UserRoleEnum.admin;"
        "db.session.commit();"
        "print('dev_user_created=', created, 'dev_user_id=', u.id);"
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
        mode = "auto"
        sql_path = DEFAULT_SQL
        for arg in sys.argv[1:]:
            if arg == "--split":
                mode = "split"
            elif arg == "--monolith":
                mode = "monolith"
            elif arg.startswith("-"):
                raise RuntimeError(f"Argomento non supportato: {arg}")
            else:
                sql_path = Path(arg).resolve()
        log("[start] import_cached_migrated_sql")
        if mode == "auto":
            mode = "split" if ORDER_FILE.exists() else "monolith"
        log(f"[info] mode={mode}")
        log(f"[info] sql_path={sql_path}")
        ensure_enum_values(db_url)
        if mode == "split":
            import_split_tables(db_url, ORDER_FILE)
        else:
            import_sql(db_url, sql_path)
        normalize_legacy_statoclienteenum_values(db_url)
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
