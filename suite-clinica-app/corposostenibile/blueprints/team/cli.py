"""
team.cli
========

Flask-CLI utilities per la gestione rapida degli utenti.
"""

from __future__ import annotations

import click
from flask.cli import AppGroup
from werkzeug.security import generate_password_hash

from corposostenibile.extensions import db
from corposostenibile.models import User

team_cli = AppGroup("team", help="Gestione utenti interni")


# ------------------------------------------------------------- weekly-report-reminder
@team_cli.command("send-report-reminder")
@click.argument("email", required=False)
def send_report_reminder(email):
    """Invia reminder report settimanale (test)."""
    from .weekly_report_tasks import send_test_reminder, send_weekly_report_reminders_task
    
    if email:
        # Test singolo utente
        if send_test_reminder(email):
            click.echo(click.style(f"✅ Reminder inviato a {email}", fg="green"))
        else:
            click.echo(click.style(f"❌ Errore: utente {email} non trovato", fg="red"))
    else:
        # Invia a tutti
        with click.get_current_context().obj:
            result = send_weekly_report_reminders_task()
            click.echo(click.style(f"✅ Inviati {result['sent']} reminder", fg="green"))
            if result['failed'] > 0:
                click.echo(click.style(f"⚠️  {result['failed']} invii falliti", fg="yellow"))
            click.echo(f"📊 Totale utenti da notificare: {result['total']}")


# ------------------------------------------------------------- add-user
@team_cli.command("add-user")
@click.argument("email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--admin/--no-admin", default=False, show_default=True, help="Ruolo admin?")
def add_user(email: str, password: str, admin: bool):
    """Crea un nuovo utente via riga di comando."""
    email = email.lower().strip()
    if User.query.filter_by(email=email).first():
        click.echo(click.style("❌ Esiste già un utente con questa email.", fg="red"))
        raise SystemExit(1)

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=admin,
        active=True,
    )
    db.session.add(user)
    db.session.commit()
    click.echo(click.style(f"✅ Utente {email} creato (admin={admin}).", fg="green"))


# ------------------------------------------------------------- list
@team_cli.command("list")
def list_users():
    """Elenca tutti gli utenti."""
    rows = User.query.order_by(User.id).all()
    width = 30
    click.echo(f"{'ID':<5}{'EMAIL':<{width}}ADMIN  ACTIVE")
    click.echo("-" * (width + 20))
    for u in rows:
        click.echo(
            f"{u.id:<5}{u.email:<{width}}{'✔' if u.is_admin else '–':^5}  {'✔' if u.active else '–':^6}"
        )
    click.echo(f"\nTotale: {len(rows)}")


# ------------------------------------------------------------- reset-pw
@team_cli.command("reset-pw")
@click.argument("email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def reset_pw(email: str, password: str):
    """Reset della password per *email* specificata."""
    user = User.query.filter_by(email=email.lower().strip()).first()
    if not user:
        click.echo(click.style("❌ Utente non trovato.", fg="red"))
        raise SystemExit(1)

    user.password_hash = generate_password_hash(password)
    db.session.commit()
    click.echo(click.style("✅ Password aggiornata.", fg="green"))
