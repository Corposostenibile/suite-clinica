"""
CLI commands per il blueprint ghl_support.

Comandi principali:
- ``flask ghl-support register-webhook``    registra webhook ClickUp GHL
- ``flask ghl-support list-webhooks``       mostra webhook registrati
- ``flask ghl-support delete-webhook <id>`` rimuove webhook
- ``flask ghl-support test-create``         crea task di prova su ClickUp
- ``flask ghl-support test-sso-url``        stampa URL di test con placeholder
"""

from __future__ import annotations

import json
import urllib.parse

import click
from flask import Flask, current_app
from flask.cli import AppGroup

from .services import ClickUpClient, ClickUpError

ghl_support_cli = AppGroup(
    "ghl-support",
    help="Gestione integrazione GHL Support ↔ ClickUp.",
)


def register_cli_commands(app: Flask) -> None:
    app.cli.add_command(ghl_support_cli)


@ghl_support_cli.command("register-webhook")
@click.option(
    "--endpoint",
    help="URL pubblico del webhook. Default da CLICKUP_GHL_WEBHOOK_URL.",
)
@click.option(
    "--events",
    default="taskStatusUpdated,taskCommentPosted,taskUpdated,taskDeleted",
    help="Eventi ClickUp da iscrivere (separati da virgola).",
)
def register_webhook(endpoint: str | None, events: str) -> None:
    """Registra il webhook ClickUp sullo Space GHL."""
    client = ClickUpClient.from_app_config(current_app)
    endpoint_url = endpoint or current_app.config.get("CLICKUP_GHL_WEBHOOK_URL") or ""
    if not endpoint_url:
        raise click.UsageError(
            "Nessun endpoint specificato. Usa --endpoint o imposta CLICKUP_GHL_WEBHOOK_URL."
        )
    secret = current_app.config.get("CLICKUP_GHL_WEBHOOK_SECRET") or None
    space_id = current_app.config.get("CLICKUP_GHL_SPACE_ID") or None
    event_list = [e.strip() for e in events.split(",") if e.strip()]

    try:
        result = client.create_webhook(
            endpoint_url=endpoint_url,
            events=event_list,
            space_id=space_id,
            secret=secret,
        )
    except ClickUpError as exc:
        click.echo(f"[X] Errore: {exc}", err=True)
        raise SystemExit(1)

    click.echo("[OK] Webhook GHL registrato su ClickUp.")
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    if isinstance(result, dict):
        w = result.get("webhook") or result
        if w.get("secret"):
            click.echo()
            click.echo("IMPORTANTE — Salva questo secret in .env come:")
            click.echo(f"CLICKUP_GHL_WEBHOOK_SECRET={w['secret']}")


@ghl_support_cli.command("list-webhooks")
def list_webhooks() -> None:
    """Mostra i webhook registrati nel workspace ClickUp."""
    client = ClickUpClient.from_app_config(current_app)
    try:
        result = client.list_webhooks()
    except ClickUpError as exc:
        click.echo(f"[X] Errore: {exc}", err=True)
        raise SystemExit(1)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@ghl_support_cli.command("delete-webhook")
@click.argument("webhook_id")
def delete_webhook(webhook_id: str) -> None:
    """Rimuove un webhook ClickUp."""
    client = ClickUpClient.from_app_config(current_app)
    try:
        client.delete_webhook(webhook_id)
    except ClickUpError as exc:
        click.echo(f"[X] Errore: {exc}", err=True)
        raise SystemExit(1)
    click.echo(f"[OK] Webhook {webhook_id} eliminato.")


@ghl_support_cli.command("test-create")
@click.option("--title", default="[TEST] Ticket GHL di prova dalla CLI")
def test_create(title: str) -> None:
    """Crea un task di test su ClickUp GHL (per verifica integrazione)."""
    client = ClickUpClient.from_app_config(current_app)
    try:
        task = client.create_task(
            name=title,
            description="Task di test generato da `flask ghl-support test-create`.",
            tags=["test", "cli", "origine:ghl"],
        )
    except ClickUpError as exc:
        click.echo(f"[X] Errore: {exc}", err=True)
        raise SystemExit(1)
    click.echo("[OK] Task creato.")
    click.echo(f"ID: {task.get('id')}")
    click.echo(f"URL: {task.get('url')}")


@ghl_support_cli.command("test-sso-url")
@click.option("--base-url", help="Base URL del frontend (es. https://<tunnel>)")
@click.option("--user-id", default="test-user-001")
@click.option("--user-email", default="test@corposostenibile.it")
@click.option("--user-name", default="Test Sales")
@click.option("--location-id", default="test-loc-001")
@click.option("--location-name", default="Sede Test")
@click.option("--role", default="user")
def test_sso_url(
    base_url: str | None,
    user_id: str,
    user_email: str,
    user_name: str,
    location_id: str,
    location_name: str,
    role: str,
) -> None:
    """
    Stampa un URL di test con i placeholder GHL già espansi, da incollare nel
    browser per simulare l'accesso dal Custom Menu Link.
    """
    base = base_url or current_app.config.get("CLICKUP_GHL_WEBHOOK_URL", "").replace(
        "/webhooks/clickup-ghl", ""
    )
    if not base:
        raise click.UsageError("Passa --base-url o imposta CLICKUP_GHL_WEBHOOK_URL")

    params = {
        "user_id": user_id,
        "user_email": user_email,
        "user_name": user_name,
        "location_id": location_id,
        "location_name": location_name,
        "role": role,
    }
    qs = urllib.parse.urlencode(params)
    url = f"{base.rstrip('/')}/ghl-embed/tickets?{qs}"

    click.echo("URL di test (apri in browser per simulare GHL):")
    click.echo(url)
