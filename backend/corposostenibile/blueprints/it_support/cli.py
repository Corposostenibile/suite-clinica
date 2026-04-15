"""
CLI commands per il blueprint it_support.

Comandi principali:
- ``flask it-support register-webhook``     registra webhook ClickUp
- ``flask it-support list-webhooks``        mostra i webhook registrati
- ``flask it-support delete-webhook <id>``  rimuove un webhook
- ``flask it-support test-create``          crea un task di prova su ClickUp
"""

from __future__ import annotations

import json

import click
from flask import Flask, current_app
from flask.cli import AppGroup

from .services import ClickUpClient, ClickUpError

it_support_cli = AppGroup(
    "it-support",
    help="Gestione integrazione IT Support ↔ ClickUp.",
)


def register_cli_commands(app: Flask) -> None:
    app.cli.add_command(it_support_cli)


@it_support_cli.command("register-webhook")
@click.option(
    "--endpoint",
    help="URL pubblico del webhook. Se omesso usa CLICKUP_WEBHOOK_URL dall'env.",
)
@click.option(
    "--events",
    default="taskStatusUpdated,taskCommentPosted,taskUpdated,taskDeleted",
    help="Eventi ClickUp da iscrivere (separati da virgola).",
)
def register_webhook(endpoint: str | None, events: str) -> None:
    """Registra il webhook ClickUp puntato al backend."""
    client = ClickUpClient.from_app_config(current_app)
    endpoint_url = endpoint or current_app.config.get("CLICKUP_WEBHOOK_URL") or ""
    if not endpoint_url:
        raise click.UsageError(
            "Nessun endpoint specificato. Usa --endpoint o imposta CLICKUP_WEBHOOK_URL."
        )
    secret = current_app.config.get("CLICKUP_WEBHOOK_SECRET") or None
    space_id = current_app.config.get("CLICKUP_SPACE_ID") or None
    event_list = [e.strip() for e in events.split(",") if e.strip()]

    try:
        result = client.create_webhook(
            endpoint_url=endpoint_url,
            events=event_list,
            space_id=space_id,
            secret=secret,
        )
    except ClickUpError as exc:
        click.echo(f"❌  Errore: {exc}", err=True)
        raise SystemExit(1)

    click.echo("✅  Webhook registrato su ClickUp.")
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@it_support_cli.command("list-webhooks")
def list_webhooks() -> None:
    """Mostra i webhook registrati nel workspace ClickUp."""
    client = ClickUpClient.from_app_config(current_app)
    try:
        result = client.list_webhooks()
    except ClickUpError as exc:
        click.echo(f"❌  Errore: {exc}", err=True)
        raise SystemExit(1)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@it_support_cli.command("delete-webhook")
@click.argument("webhook_id")
def delete_webhook(webhook_id: str) -> None:
    """Rimuove un webhook ClickUp."""
    client = ClickUpClient.from_app_config(current_app)
    try:
        client.delete_webhook(webhook_id)
    except ClickUpError as exc:
        click.echo(f"❌  Errore: {exc}", err=True)
        raise SystemExit(1)
    click.echo(f"🗑️   Webhook {webhook_id} eliminato.")


@it_support_cli.command("test-create")
@click.option(
    "--title",
    default="[TEST] Ticket di prova dalla CLI",
    help="Titolo del task di test.",
)
def test_create(title: str) -> None:
    """Crea un task di test su ClickUp (per verifica integrazione)."""
    client = ClickUpClient.from_app_config(current_app)
    try:
        task = client.create_task(
            name=title,
            description="Task di test generato da `flask it-support test-create`.",
            priority=3,
            tags=["test", "cli"],
        )
    except ClickUpError as exc:
        click.echo(f"❌  Errore: {exc}", err=True)
        raise SystemExit(1)
    click.echo("✅  Task creato.")
    click.echo(f"ID: {task.get('id')}")
    click.echo(f"URL: {task.get('url')}")
