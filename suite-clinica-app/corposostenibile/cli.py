"""cli.py – CLI helpers · Corposostenibile Suite 4.1
===================================================

Registra sull'oggetto **Flask** tutti i comandi custom messi a
disposizione dall'applicazione e dagli script esterni.

Comandi principali
------------------
* **create-db / drop-db**  → gestione schema + ENUM
* **seed / seed-dummy**    → popolamento dati iniziali
* **import-xlsx**          → legacy (import di un singolo workbook clienti)
* **import-xlsx-all**      → nuovo importer universale (clienti + contabilità)
* **import-contabilita**   → alias comodo di *import‑xlsx‑all*
* **import-clienti**       → import SOLO clienti dal Database Clienti Excel
* **export-csv**           → dump tabelle in CSV
* **create-admin**         → crea il primo super‑utente

Mostra l'elenco completo con::

    flask --app corposostenibile --help
"""
from __future__ import annotations

# ─────────────────────────── stdlib / typing ────────────────────────────
import importlib
from types import ModuleType
from typing import Callable, Dict

# "Path" è usato da alcuni script esterni che lo importano da qui
from pathlib import Path   # noqa: F401 – re‑export convenience

# ────────────────────────────── 3rd‑party ───────────────────────────────
import click
from flask import Flask
from sqlalchemy import text
from sqlalchemy.engine import Engine

# ─────────────────────────────── app core ───────────────────────────────
from .extensions import db
from .models import register_enums   # crea gli ENUM Postgres se mancanti

__all__ = [
    "register_cli_commands",
]

# ═══════════════════════ 1. Comandi di base DB ══════════════════════════

def _register_basic_commands(app: Flask) -> None:  # pragma: no cover
    """Registra **create-db** e **drop-db**."""

    @app.cli.command("create-db")
    def create_db() -> None:
        """Crea tutte le tabelle + ENUM (idempotente)."""
        register_enums()
        db.create_all()
        click.echo("✅  Database tables + enums created.")

    @app.cli.command("drop-db")
    @click.option("--force", "-f", is_flag=True, help="Salta la conferma interattiva.")
    def drop_db(force: bool = False) -> None:
        """Elimina l'intero schema (tabelle **e** ENUM)."""
        if not force and not click.confirm("Are you sure you want to DROP **ALL** tables?"):
            click.echo("❎  Abort.")
            return

        engine: Engine = db.get_engine()
        if engine.dialect.name == "postgresql":
            # Operazione atomica (serve AUTOCOMMIT).
            with engine.connect() as conn:
                conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
            click.echo("🗑️  Dropped PostgreSQL schema 'public'.")
        else:
            db.drop_all()
            click.echo("🗑️  Dropped all tables.")

# ═══════════════════ 2. Comandi caricati dinamicamente ═════════════════
# Ogni modulo indicato deve esporre una funzione  register(app)


_SCRIPT_MAP: Dict[str, str] = {
    # alias               : modulo che contiene  register(app)
    # --------------------------------------------------------------
    # Nessuno script esterno configurato al momento
    # Aggiungi qui eventuali script futuri se necessario
}


def _dynamic_register(app: Flask, alias: str, module_path: str) -> None:
    """Importa *module_path* e registra il relativo comando su *app*.
    Se il modulo o la funzione `register` non esistono, logga un warning.
    """
    try:
        mod: ModuleType = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        click.echo(f"⚠️  {module_path} not found – comando '{alias}' ignorato  ➜  {exc}")
        return

    register_fn: Callable[[Flask], None] | None = getattr(mod, "register", None)
    if register_fn is None:
        click.echo(f"⚠️  {module_path}.register() mancante – comando '{alias}' ignorato.")
        return

    register_fn(app)


def _register_external_commands(app: Flask) -> None:
    """Cicla su *_SCRIPT_MAP* e registra tutti i comandi runtime."""
    for alias, module_path in _SCRIPT_MAP.items():
        _dynamic_register(app, alias, module_path)

# ═════════════════════ 3. Entry‑point pubblico ═════════════════════════

def register_cli_commands(app: Flask) -> None:
    """Hook da chiamare dentro l'application‑factory."""
    _register_basic_commands(app)
    _register_external_commands(app)