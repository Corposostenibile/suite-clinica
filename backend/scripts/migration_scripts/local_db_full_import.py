#!/usr/bin/env python3
"""
Migrazione locale "old suite -> new schema" usando schema_comparator.py.

Pipeline:
1) Reset DB target locale (drop/create)
2) Inizializza schema nuovo corrente del progetto (oppure usa SQL passato)
3) Esegue schema_comparator.py per generare SQL migrato dai dati old
4) Importa SQL migrato nel DB locale

Esempio:
  poetry run python scripts/migration_scripts/local_db_full_import.py \
    --old-suite-backup /data/backups/old_suite_backups/old_suite.dump \
    --target-url postgresql://suite_clinica:password@localhost:5432/suite_clinica_dev_manu \
    --yes
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> None:
    print(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def check_binaries(bins: list[str]) -> None:
    missing = [b for b in bins if shutil.which(b) is None]
    if missing:
        raise RuntimeError(f"Binary mancanti: {', '.join(missing)}")


def load_database_url_from_backend_env() -> str | None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    return None


def admin_db_url(target_url: str) -> tuple[str, str]:
    parsed = urlparse(target_url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise ValueError("Target URL senza nome DB.")
    admin_parsed = parsed._replace(path="/postgres")
    return urlunparse(admin_parsed), db_name


def reset_target_db(target_url: str, dry_run: bool) -> None:
    admin_url, db_name = admin_db_url(target_url)
    ident = quote_ident(db_name)
    db_name_esc = db_name.replace("'", "''")
    if dry_run:
        print("[dry-run] reset target db")
        print(
            "\n".join(
                [
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();",
                    f"DROP DATABASE IF EXISTS {ident};",
                    f"CREATE DATABASE {ident};",
                ]
            )
        )
        return
    run_cmd(
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
        run_cmd(["psql", admin_url, "-v", "ON_ERROR_STOP=1", "-c", f"CREATE DATABASE {ident};"])
        return

    print(
        "[warn] DROP DATABASE fallito (probabile ownership). "
        "Fallback: reset completo schema public nel DB target."
    )
    run_cmd(
        [
            "psql",
            target_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO CURRENT_USER;",
        ]
    )


def apply_schema(target_url: str, schema_sql: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] apply schema: {schema_sql}")
        return
    run_cmd(["psql", target_url, "-v", "ON_ERROR_STOP=1", "-f", str(schema_sql)])


def init_schema_from_current_project(target_url: str, dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] init schema from current project models (db.create_all)")
        return
    env = os.environ.copy()
    env["DATABASE_URL"] = target_url
    code = (
        "from corposostenibile import create_app;"
        "from corposostenibile.extensions import db;"
        "app=create_app();"
        "ctx=app.app_context();ctx.push();"
        "db.create_all();"
        "ctx.pop()"
    )
    run_cmd([sys.executable, "-c", code], env=env)


def dump_schema_from_target(target_url: str, out_sql: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] dump schema-only from target db -> {out_sql}")
        return
    run_cmd(
        [
            "pg_dump",
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(out_sql),
            target_url,
        ]
    )


def run_schema_comparator(
    comparator_script: Path,
    new_schema_backup: Path,
    old_suite_backup: Path,
    output_sql: Path,
    dry_run: bool,
) -> None:
    env = os.environ.copy()
    env["NEW_SUITE_BACKUP"] = str(new_schema_backup)
    env["OLD_SUITE_BACKUP"] = str(old_suite_backup)
    env["OUTPUT_FILE"] = str(output_sql)

    cmd = [sys.executable, str(comparator_script)]
    if dry_run:
        print("[dry-run] generate migrated SQL with schema_comparator")
        print(f"[env] NEW_SUITE_BACKUP={new_schema_backup}")
        print(f"[env] OLD_SUITE_BACKUP={old_suite_backup}")
        print(f"[env] OUTPUT_FILE={output_sql}")
        print(f"[cmd] {' '.join(cmd)}")
        return
    run_cmd(cmd, env=env)


def import_migrated_sql(target_url: str, migrated_sql: Path, on_error_stop: bool, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] import migrated SQL: {migrated_sql}")
        return
    stop_flag = "1" if on_error_stop else "0"
    run_cmd(["psql", target_url, "-v", f"ON_ERROR_STOP={stop_flag}", "-f", str(migrated_sql)])
    run_cmd(["psql", target_url, "-v", "ON_ERROR_STOP=1", "-c", "ANALYZE;"])


def verify_result(target_url: str, dry_run: bool) -> None:
    sql = """
SELECT 'tables', COUNT(*)::text
FROM information_schema.tables
WHERE table_schema='public'
UNION ALL
SELECT 'users', COUNT(*)::text FROM public.users
UNION ALL
SELECT 'clienti', COUNT(*)::text FROM public.clienti
UNION ALL
SELECT 'push_subscriptions', COUNT(*)::text
FROM information_schema.tables
WHERE table_schema='public' AND table_name='push_subscriptions';
"""
    if dry_run:
        print("[dry-run] verify result")
        return
    run_cmd(["psql", target_url, "-v", "ON_ERROR_STOP=1", "-At", "-F", "|", "-c", sql])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Esegue migrazione completa old->new schema e importa nel DB locale."
    )
    p.add_argument(
        "--new-schema-backup",
        help="File SQL schema nuova suite. Se omesso usa schema corrente del progetto.",
    )
    p.add_argument("--old-suite-backup", required=True, help="Dump old suite (pg_dump custom).")
    p.add_argument(
        "--target-url",
        help="DB locale target. Default: DATABASE_URL o backend/.env",
    )
    p.add_argument(
        "--schema-comparator",
        default=str(Path(__file__).resolve().parent / "schema_comparator.py"),
        help="Path script schema_comparator.py",
    )
    p.add_argument("--workdir", default="", help="Dir temporanea (default: temp system).")
    p.add_argument("--keep-migrated-sql", action="store_true", help="Mantiene SQL generato.")
    p.add_argument("--continue-on-error", action="store_true", help="Import psql con ON_ERROR_STOP=0.")
    p.add_argument("--yes", action="store_true", help="Salta conferma interattiva.")
    p.add_argument("--dry-run", action="store_true", help="Simula senza eseguire.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        check_binaries(["psql", "pg_restore", "python3"])

        old_suite_backup = Path(args.old_suite_backup).resolve()
        comparator_script = Path(args.schema_comparator).resolve()

        new_schema_backup: Path | None = None
        if args.new_schema_backup:
            new_schema_backup = Path(args.new_schema_backup).resolve()
            if not new_schema_backup.exists():
                raise FileNotFoundError(f"Schema backup non trovato: {new_schema_backup}")
        if not old_suite_backup.exists():
            raise FileNotFoundError(f"Old backup non trovato: {old_suite_backup}")
        if not comparator_script.exists():
            raise FileNotFoundError(f"schema_comparator non trovato: {comparator_script}")

        target_url = (
            args.target_url
            or os.environ.get("DATABASE_URL")
            or load_database_url_from_backend_env()
        )
        if not target_url:
            raise RuntimeError("Target URL non trovato. Passa --target-url o imposta DATABASE_URL.")

        if not args.yes and not args.dry_run:
            print(f"ATTENZIONE: il DB target verrà RECREATO da zero:\n  {target_url}")
            if new_schema_backup:
                print(f"Schema nuovo: {new_schema_backup}")
            else:
                print("Schema nuovo: corrente del progetto (modelli attuali)")
            print(f"Dati old:    {old_suite_backup}")
            ans = input("Continuare? [y/N]: ").strip().lower()
            if ans not in {"y", "yes"}:
                print("Operazione annullata.")
                return 1

        tmp_ctx = None
        if args.workdir:
            wd = Path(args.workdir).resolve()
            wd.mkdir(parents=True, exist_ok=True)
            tmp_ctx = tempfile.TemporaryDirectory(prefix="local_schema_migration_", dir=str(wd))
        else:
            tmp_ctx = tempfile.TemporaryDirectory(prefix="local_schema_migration_")

        with tmp_ctx as tmp_dir:
            migrated_sql = Path(tmp_dir) / "migrated_db.sql"
            effective_schema_sql = Path(tmp_dir) / "effective_new_schema.sql"

            reset_target_db(target_url, args.dry_run)
            if new_schema_backup:
                apply_schema(target_url, new_schema_backup, args.dry_run)
                effective_schema_sql = new_schema_backup
            else:
                init_schema_from_current_project(target_url, args.dry_run)
                dump_schema_from_target(target_url, effective_schema_sql, args.dry_run)
            run_schema_comparator(
                comparator_script=comparator_script,
                new_schema_backup=effective_schema_sql,
                old_suite_backup=old_suite_backup,
                output_sql=migrated_sql,
                dry_run=args.dry_run,
            )
            import_migrated_sql(
                target_url=target_url,
                migrated_sql=migrated_sql,
                on_error_stop=not args.continue_on_error,
                dry_run=args.dry_run,
            )
            verify_result(target_url, args.dry_run)

            if args.keep_migrated_sql:
                dst_dir = Path(__file__).resolve().parents[2] / "backups" / "migration_output_local"
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / f"local_migrated_{migrated_sql.name}"
                if not args.dry_run:
                    shutil.copy2(migrated_sql, dst)
                print(f"[info] SQL migrato salvato in: {dst}")

        print("[ok] Migrazione locale completata.")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"[error] comando fallito (exit={exc.returncode}): {exc.cmd}", file=sys.stderr)
        return exc.returncode or 2
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
