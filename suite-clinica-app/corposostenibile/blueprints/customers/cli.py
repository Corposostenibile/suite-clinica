"""
customers.cli
=============

Flask-CLI commands for the **customers** blueprint.

Comandi disponibili
------------------
* **export**            – esporta lista clienti in CSV / JSON / XLSX  
* **import**            – importa in bulk da file  
* **merge-dupes**       – individua e fonde duplicati (e-mail / telefono)  
* **recalc-ltv**        – ricalcola gli indicatori LTV  
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

import click

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover
    pd = None  # type: ignore

from flask import current_app
from flask.cli import AppGroup, with_appcontext
from sqlalchemy import func

from corposostenibile.extensions import db
from corposostenibile.models import Cliente
from .services import (                       # layer “write”
    _match_cliente,                           # (cliente | None, algoritmo | None)
    bulk_create_or_update_clienti,
    calculate_ltv_for_clienti,
    find_potential_duplicates,
)

EXPORT_FORMATS: tuple[Literal["csv", "json", "xlsx"], ...] = ("csv", "json", "xlsx")

#: gruppo blueprint (registrato in customers.init_app)
customers_cli = AppGroup("customers", help="Commands for the *clienti* domain")

# ───────────────────────────── helper comuni ──────────────────────────────


def _confirm(action: str) -> None:
    """Conferma su TTY prima di operazioni distruttive."""
    if not sys.stdin.isatty():  # running in CI / pipe
        return
    click.echo(click.style(f"About to {action}.", fg="yellow"))
    if not click.confirm("Do you want to continue?", default=False):
        click.echo("Aborted.")
        sys.exit(1)


def _query_to_dataframe(rows: Iterable[Any]):
    """SQLAlchemy rows → pandas.DataFrame (senza SA state)."""
    if pd is None:  # pragma: no cover
        raise click.ClickException("Install 'pandas' to use this command.")
    out = []
    for obj in rows:
        d = obj.__dict__.copy()
        d.pop("_sa_instance_state", None)
        out.append(d)
    return pd.DataFrame(out)


# ─────────────────────────────────── EXPORT ─────────────────────────────────


@customers_cli.command("export")
@click.option(
    "--format",
    "export_fmt",
    type=click.Choice(EXPORT_FORMATS, case_sensitive=False),
    default="csv",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Target path (default ./customers_<ts>.<ext>).",
)
@click.option(
    "--filter",
    "filters_",
    multiple=True,
    help="Filter expression field=value (repeatable).",
)
@with_appcontext
def export_customers(export_fmt: str, output: Path | None, filters_: Sequence[str]):
    """Esporta i clienti in CSV / JSON / XLSX con filtri facoltativi."""
    q = db.session.query(Cliente)

    # filtri dinamici
    for expr in filters_:
        if "=" not in expr:
            raise click.BadParameter("Filter must be field=value.")
        field, value = expr.split("=", 1)
        if not hasattr(Cliente, field):
            raise click.BadParameter(f"Unknown field '{field}'.")
        q = q.filter(getattr(Cliente, field) == value)

    df = _query_to_dataframe(q.all())
    if df.empty:
        click.echo("No matching records.")
        sys.exit(0)

    if output is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output = Path.cwd() / f"customers_{ts}.{export_fmt}"

    match export_fmt:
        case "csv":
            df.to_csv(output, index=False)
        case "json":
            df.to_json(output, orient="records", date_format="iso")
        case "xlsx":
            df.to_excel(output, index=False)

    click.echo(click.style(f"Exported {len(df)} rows → {output}", fg="green"))


# ─────────────────────────────────── IMPORT ─────────────────────────────────


@customers_cli.command("import")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "import_fmt",
    type=click.Choice(EXPORT_FORMATS, case_sensitive=False),
    help="Force input format (autodetect by extension if omitted).",
)
@click.option("--dry-run", is_flag=True, help="Validate file without touching DB.")
@with_appcontext
def import_customers(input: Path, import_fmt: str | None, dry_run: bool):
    """Bulk-import / upsert dei clienti da CSV | JSON | XLSX."""
    if pd is None:
        raise click.ClickException("Install 'pandas' to use this command.")

    import_fmt = import_fmt or input.suffix.lstrip(".").lower()
    if import_fmt not in EXPORT_FORMATS:
        raise click.BadParameter("Unrecognized format; use --format.")

    df = (
        pd.read_csv(input)
        if import_fmt == "csv"
        else pd.read_json(input)
        if import_fmt == "json"
        else pd.read_excel(input)
    )

    if df.empty:
        click.echo("File vuoto — nulla da importare.")
        sys.exit(0)

    if {"nome_cognome"} - set(df.columns):
        raise click.ClickException("Column 'nome_cognome' is required.")

    records = df.to_dict(orient="records")

    if dry_run:
        click.echo(json.dumps({"would_import": len(records)}, indent=2, ensure_ascii=False))
        return

    _confirm(f"import {len(records)} customers from '{input.name}'")
    created, updated = bulk_create_or_update_clienti(records)
    db.session.commit()
    click.echo(
        click.style(f"Import complete — {created} created, {updated} updated.", fg="green")
    )


# ─────────────────────────────── MERGE DUPES ───────────────────────────────


@customers_cli.command("merge-dupes")
@click.option("--by", type=click.Choice(["email", "numero_tel"]), default="email")
@click.option("--dry-run", is_flag=True, help="Show what would be merged.")
@with_appcontext
def merge_duplicates(by: str, dry_run: bool):
    """Fonde record duplicati per e-mail o numero di telefono."""
    groups = find_potential_duplicates(key=by)
    if not groups:
        click.echo("No duplicates found.")
        return

    click.echo(f"Found {len(groups)} duplicate group(s).")
    if dry_run:
        click.echo(json.dumps(groups, indent=2, ensure_ascii=False))
        return

    _confirm("merge the detected duplicates")
    merged = 0
    for group in groups:
        keeper_id = min(item["cliente_id"] for item in group)
        keeper = db.session.get(Cliente, keeper_id)
        for dup in group:
            if dup["cliente_id"] == keeper_id:
                continue
            loser = db.session.get(Cliente, dup["cliente_id"])
            for pay in getattr(loser, "payments", []):
                pay.cliente_id = keeper_id
            for sub in getattr(loser, "subscriptions", []):
                sub.cliente_id = keeper_id
            db.session.delete(loser)
            merged += 1
    db.session.commit()
    click.echo(click.style(f"Merged {merged} records.", fg="green"))


# ─────────────────────────────── RECALC LTV ────────────────────────────────


@customers_cli.command("recalc-ltv")
@click.option("--all", "recalc_all", is_flag=True, help="Recalculate for **all**.")
@click.option(
    "--customer-id",
    type=int,
    multiple=True,
    help="Limit to specific cliente_id (repeatable).",
)
@with_appcontext
def recalc_ltv(recalc_all: bool, customer_id: tuple[int, ...]):
    """Ricalcola LTV / LTV_90 per i clienti indicati."""
    if not recalc_all and not customer_id:
        raise click.BadParameter("Specify --all or --customer-id")

    ids = (
        [row[0] for row in db.session.query(Cliente.cliente_id)]
        if recalc_all
        else list(customer_id)
    )
    click.echo(f"Recalculating LTV for {len(ids)} customer(s)…")
    calculate_ltv_for_clienti(ids)
    db.session.commit()
    click.echo(click.style("Done.", fg="green"))




# ─────────────────────────────── SEED DEMO ──────────────────────────────────


@customers_cli.command("seed-demo")
@click.option("--count", default=50, show_default=True, help="Number of clients to create.")
@click.option("--dry-run", is_flag=True, help="Show sample data without inserting.")
@with_appcontext
def seed_demo_clients(count: int, dry_run: bool):
    """Crea clienti fittizi per demo/testing."""
    import random
    from datetime import date, timedelta

    # Nomi italiani realistici
    NOMI_MASCHILI = [
        "Marco", "Luca", "Andrea", "Francesco", "Alessandro", "Matteo", "Lorenzo",
        "Davide", "Simone", "Federico", "Giacomo", "Riccardo", "Tommaso", "Nicola",
        "Gabriele", "Stefano", "Giovanni", "Pietro", "Antonio", "Roberto", "Daniele",
        "Fabio", "Paolo", "Michele", "Filippo", "Emanuele", "Vincenzo", "Giuseppe",
        "Alberto", "Massimo", "Claudio", "Enrico"
    ]
    NOMI_FEMMINILI = [
        "Giulia", "Chiara", "Francesca", "Sara", "Martina", "Valentina", "Alessia",
        "Federica", "Elisa", "Silvia", "Elena", "Laura", "Anna", "Sofia", "Aurora",
        "Alice", "Beatrice", "Giorgia", "Marta", "Roberta", "Claudia", "Serena",
        "Paola", "Monica", "Cristina", "Barbara", "Ilaria", "Arianna", "Veronica",
        "Michela", "Eleonora", "Camilla"
    ]
    COGNOMI = [
        "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
        "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini",
        "Costa", "Giordano", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana",
        "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini",
        "Leone", "Longo", "Gentile", "Martinelli", "Vitale", "Serra", "Coppola",
        "De Santis", "D'Angelo", "Marchetti", "Parisi", "Villa", "Conte", "Ferraro",
        "Ferri", "Fabbri", "Bianco", "Marini", "Grasso", "Valentini", "Messina"
    ]
    CITTA = [
        ("Milano", "MI"), ("Roma", "RM"), ("Napoli", "NA"), ("Torino", "TO"),
        ("Firenze", "FI"), ("Bologna", "BO"), ("Venezia", "VE"), ("Genova", "GE"),
        ("Palermo", "PA"), ("Bari", "BA"), ("Catania", "CT"), ("Verona", "VR"),
        ("Padova", "PD"), ("Trieste", "TS"), ("Brescia", "BS"), ("Parma", "PR"),
        ("Modena", "MO"), ("Reggio Emilia", "RE"), ("Perugia", "PG"), ("Cagliari", "CA")
    ]
    PROFESSIONI = [
        "Impiegato/a", "Libero professionista", "Manager", "Insegnante", "Ingegnere",
        "Medico", "Avvocato", "Commercialista", "Architetto", "Designer",
        "Sviluppatore software", "Marketing specialist", "Consulente", "Imprenditore",
        "Studente universitario", "Ricercatore", "Giornalista", "Infermiere/a",
        "Personal trainer", "Fotografo", "Chef", "Commerciante"
    ]
    STATI = ["attivo", "attivo", "attivo", "attivo", "ghost", "pausa", "stop"]  # Weighted
    TIPOLOGIE = ["a", "a", "b", "b", "c", "recupero", "pausa_gt_30"]  # Weighted
    PAGAMENTI = ["bonifico", "stripe", "paypal", "carta", "klarna"]
    GIORNI_CHECK = ["lun", "mar", "mer", "gio", "ven"]
    LUOGHI = ["casa", "palestra", "ibrido"]
    TEAMS = ["interno", "sales_team", "setter_team", "sito"]
    DURATE = [90, 180, 365]

    click.echo(f"Generating {count} demo clients...")
    created = 0
    samples = []

    for i in range(count):
        # Genere
        is_female = random.random() < 0.55  # Slightly more female clients
        genere = "donna" if is_female else "uomo"
        nome = random.choice(NOMI_FEMMINILI if is_female else NOMI_MASCHILI)
        cognome = random.choice(COGNOMI)
        nome_cognome = f"{nome} {cognome}"

        # Data nascita (25-55 anni)
        today = date.today()
        age = random.randint(25, 55)
        birth_year = today.year - age
        data_nascita = date(birth_year, random.randint(1, 12), random.randint(1, 28))

        # Contact
        email_domain = random.choice(["gmail.com", "outlook.it", "yahoo.it", "libero.it", "hotmail.it"])
        email = f"{nome.lower()}.{cognome.lower()}{random.randint(1, 99)}@{email_domain}"
        telefono = f"+39 3{random.randint(20, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}"

        # Location
        citta, prov = random.choice(CITTA)
        via = f"Via {random.choice(['Roma', 'Milano', 'Dante', 'Garibaldi', 'Mazzini', 'Verdi', 'Leopardi'])}, {random.randint(1, 150)}"
        indirizzo = f"{via}, {citta} ({prov})"

        # Subscription
        days_ago = random.randint(30, 400)
        data_inizio = today - timedelta(days=days_ago)
        durata = random.choice(DURATE)
        data_rinnovo = data_inizio + timedelta(days=durata)

        # Stato basato su data rinnovo
        stato = random.choice(STATI)
        if data_rinnovo < today:
            stato = random.choice(["ghost", "stop", "pausa"])

        # Altri campi
        deposito = random.choice([0, 50, 100, 150, 200, 250, 300])
        ltv = random.randint(500, 5000)

        # Psicologia
        sedute_comprate = random.choice([0, 0, 0, 4, 8, 12])
        sedute_svolte = min(sedute_comprate, random.randint(0, sedute_comprate)) if sedute_comprate > 0 else 0

        cliente_data = {
            # Anagrafica
            "nome_cognome": nome_cognome,
            "data_di_nascita": data_nascita,
            "genere": genere,
            "mail": email,
            "numero_telefono": telefono,
            "indirizzo": indirizzo,
            "paese": "Italia",
            "professione": random.choice(PROFESSIONI),
            # Abbonamento
            "data_inizio_abbonamento": data_inizio,
            "durata_programma_giorni": durata,
            "data_rinnovo": data_rinnovo,
            "deposito_iniziale": deposito,
            "modalita_pagamento": random.choice(PAGAMENTI),
            "rate_cliente_sales": ltv,
            # Programma
            "tipologia_cliente": random.choice(TIPOLOGIE),
            "di_team": random.choice(TEAMS),
            # Stati
            "stato_cliente": stato,
            # Planning
            "check_day": random.choice(GIORNI_CHECK),
            "luogo_di_allenamento": random.choice(LUOGHI),
            # Psicologia
            "sedute_psicologia_comprate": sedute_comprate,
            "sedute_psicologia_svolte": sedute_svolte,
        }

        samples.append(cliente_data)

        if not dry_run:
            cliente = Cliente(**cliente_data)
            db.session.add(cliente)
            created += 1

    if dry_run:
        # Show first 3 samples
        click.echo("\nSample data (first 3):")
        for s in samples[:3]:
            display = {k: str(v) for k, v in s.items()}
            click.echo(json.dumps(display, indent=2, ensure_ascii=False))
        click.echo(f"\n... and {len(samples) - 3} more.")
        return

    db.session.commit()
    click.echo(click.style(f"\nCreated {created} demo clients successfully!", fg="green"))

    # Show stats
    attivi = sum(1 for s in samples if s["stato_cliente"] == "attivo")
    ghost = sum(1 for s in samples if s["stato_cliente"] == "ghost")
    click.echo(f"  - Attivi: {attivi}")
    click.echo(f"  - Ghost: {ghost}")
    click.echo(f"  - Altri: {count - attivi - ghost}")


# ─────────────────────────── register_cli (init_app) ───────────────────────


def register_cli(app):  # noqa: D401
    """Attach this module's commands to *app*."""
    app.cli.add_command(customers_cli)
