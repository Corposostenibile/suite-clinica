from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DUMP_DIR = BACKEND_DIR / "backups" / "prod_db_local"
DEFAULT_DUMP_FILE = DEFAULT_DUMP_DIR / "prod_db.dump"


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"{ts()} {msg}", flush=True)


def fmt_seconds(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    log(f"[cmd] {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, text=True, capture_output=True, env=env)


def run_passthrough(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    log(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def load_database_url_from_env_file(key: str = "DATABASE_URL") -> str:
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env non trovato: {env_path}")
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"{key} non trovato in {env_path}")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def admin_db_url(target_url: str) -> tuple[str, str]:
    parsed = urlparse(target_url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise RuntimeError("DATABASE_URL target senza nome DB")
    return urlunparse(parsed._replace(path="/postgres")), db_name


def reset_target_db(target_url: str) -> None:
    admin_url, db_name = admin_db_url(target_url)
    ident = quote_ident(db_name)
    db_name_esc = db_name.replace("'", "''")
    run_passthrough(
        [
            "psql",
            admin_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name_esc}' AND pid <> pg_backend_pid();",
        ]
    )
    drop_cmd = ["psql", admin_url, "-v", "ON_ERROR_STOP=1", "-c", f"DROP DATABASE IF EXISTS {ident};"]
    drop_res = subprocess.run(drop_cmd)
    if drop_res.returncode == 0:
        run_passthrough(["psql", admin_url, "-v", "ON_ERROR_STOP=1", "-c", f"CREATE DATABASE {ident};"])
        return

    log("[warn] DROP DATABASE fallito (ownership?). Fallback: reset schema public.")
    run_passthrough(
        [
            "psql",
            target_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO CURRENT_USER;",
        ]
    )


def detect_dump_kind(path: Path) -> str:
    with path.open("rb") as fh:
        head = fh.read(8)
    if head.startswith(b"PGDMP"):
        return "custom"
    return "plain"


def dump_production_db(source_url: str, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    log(f"[step] dump produzione -> {out_file}")
    run_passthrough(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(out_file),
            source_url,
        ]
    )
    log(f"[step] dump produzione completato in {fmt_seconds(time.time() - started)}")


def restore_dump_to_local(target_url: str, dump_file: Path) -> None:
    if not dump_file.exists():
        raise FileNotFoundError(f"Dump non trovato: {dump_file}")
    kind = detect_dump_kind(dump_file)
    started = time.time()
    log(f"[step] restore locale da dump ({kind})")
    reset_target_db(target_url)
    if kind == "custom":
        run_passthrough(
            [
                "pg_restore",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                "--dbname",
                target_url,
                str(dump_file),
            ]
        )
    else:
        # Compatibilità con dump generati da versioni pg_dump più nuove del psql locale
        # (es. PG16+ con "SET transaction_timeout = 0;").
        with tempfile.NamedTemporaryFile(prefix="prod_db_plain_", suffix=".sql", delete=False) as tf:
            filtered_path = Path(tf.name)
        try:
            with dump_file.open("r", encoding="utf-8", errors="ignore") as src, filtered_path.open(
                "w", encoding="utf-8"
            ) as dst:
                for line in src:
                    if line.startswith("SET transaction_timeout"):
                        continue
                    dst.write(line)
            run_passthrough(
                [
                    "psql",
                    target_url,
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-f",
                    str(filtered_path),
                ]
            )
        finally:
            try:
                filtered_path.unlink(missing_ok=True)
            except Exception:
                pass
    run_passthrough(["psql", target_url, "-v", "ON_ERROR_STOP=1", "-c", "ANALYZE;"])
    log(f"[step] restore locale completato in {fmt_seconds(time.time() - started)}")


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


def usage() -> str:
    return (
        "Uso:\n"
        "  poetry run python scripts/local_db_ops/import_cached_migrated_sql.py --source-url <PROD_DATABASE_URL> [--dump-file <path>] [--keep-dump]\n"
        "  poetry run python scripts/local_db_ops/import_cached_migrated_sql.py --dump-file <path>\n\n"
        "Note:\n"
        "  - DATABASE_URL locale letto da env o backend/.env\n"
        "  - Nessun reset utente dev: il DB viene importato 'as is' dalla produzione\n"
    )


def parse_args(argv: list[str]) -> dict[str, object]:
    source_url: str | None = None
    dump_file: Path | None = None
    keep_dump = False
    use_temp_dump = False

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--source-url":
            i += 1
            if i >= len(argv):
                raise RuntimeError("Manca valore per --source-url")
            source_url = argv[i]
        elif a == "--dump-file":
            i += 1
            if i >= len(argv):
                raise RuntimeError("Manca valore per --dump-file")
            dump_file = Path(argv[i]).resolve()
        elif a == "--keep-dump":
            keep_dump = True
        elif a in {"-h", "--help"}:
            print(usage())
            raise SystemExit(0)
        else:
            raise RuntimeError(f"Argomento non supportato: {a}")
        i += 1

    if not source_url and not dump_file:
        source_url = os.environ.get("PROD_DATABASE_URL", "").strip() or None
        if not source_url and DEFAULT_DUMP_FILE.exists():
            dump_file = DEFAULT_DUMP_FILE

    if source_url and dump_file is None:
        dump_file = DEFAULT_DUMP_FILE
    if source_url and dump_file and not keep_dump and dump_file == DEFAULT_DUMP_FILE:
        keep_dump = True  # cache locale di default
    if source_url and dump_file and dump_file.name == "":
        raise RuntimeError("Dump file non valido")

    return {
        "source_url": source_url,
        "dump_file": dump_file,
        "keep_dump": keep_dump,
        "use_temp_dump": use_temp_dump,
    }


def main() -> int:
    try:
        started = time.time()
        args = parse_args(sys.argv[1:])
        target_url = os.environ.get("DATABASE_URL") or load_database_url_from_env_file("DATABASE_URL")
        source_url = args["source_url"]
        dump_file = args["dump_file"]
        keep_dump = bool(args["keep_dump"])

        if not dump_file:
            raise RuntimeError("Serve --source-url oppure --dump-file (o DEFAULT_DUMP_FILE esistente)")

        dump_path = Path(dump_file)
        temp_file: tempfile.NamedTemporaryFile | None = None
        if source_url:
            if not keep_dump:
                temp_file = tempfile.NamedTemporaryFile(prefix="prod_db_", suffix=".dump", delete=False)
                temp_file.close()
                dump_path = Path(temp_file.name)
            log("[start] import DB produzione -> locale")
            dump_production_db(str(source_url), dump_path)
        else:
            log("[start] restore dump produzione già disponibile -> locale")

        restore_dump_to_local(target_url, dump_path)
        show_counts(target_url)
        log(f"[ok] Import DB produzione completato (durata totale={fmt_seconds(time.time() - started)})")

        if temp_file is not None:
            try:
                dump_path.unlink(missing_ok=True)
            except Exception:
                pass
        return 0
    except subprocess.CalledProcessError as exc:
        print(exc.stdout or "", end="")
        print(exc.stderr or "", end="", file=sys.stderr)
        print(f"{ts()} [error] comando fallito (exit={exc.returncode}): {exc.cmd}", file=sys.stderr)
        return exc.returncode or 2
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        print(f"{ts()} [error] {exc}", file=sys.stderr)
        print(usage(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
