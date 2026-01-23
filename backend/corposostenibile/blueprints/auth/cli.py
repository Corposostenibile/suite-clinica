"""
auth.cli
========

Comandi *Flask-CLI* per la gestione **utente / password**.

Usage rapido
------------

❯ flask auth create-user alice@example.com --admin
❯ flask auth set-password alice@example.com
❯ flask auth list-users
"""

from __future__ import annotations

import secrets
import sys
from getpass import getpass
from typing import List

import click
from flask.cli import AppGroup, with_appcontext
from werkzeug.security import generate_password_hash

from corposostenibile.extensions import db
from corposostenibile.models import User

#: comando principale – sarà registrato in `register_cli(app)`
auth_cli = AppGroup("auth", help="Gestione utenti e password")


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #
def _echo_user(u: User) -> None:
    role = "admin" if u.is_admin else "user"
    click.echo(f"[{u.id:>4}] {u.email:<30} {role}")


def _prompt_password(prompt: str = "Password") -> str:
    """Maschera input e ripete finché le due entry coincidono."""
    while True:
        pw1 = getpass(f"{prompt}: ")
        if len(pw1) < 8:
            click.echo("⚠️  Minimo 8 caratteri.")
            continue
        pw2 = getpass("Conferma: ")
        if pw1 != pw2:
            click.echo("Le password non coincidono, riprova.")
            continue
        return pw1


# --------------------------------------------------------------------------- #
#  List users                                                                 #
# --------------------------------------------------------------------------- #
@auth_cli.command("list-users")
@with_appcontext
def list_users() -> None:
    """Elenca tutti gli utenti registrati."""
    users: List[User] = User.query.order_by(User.id).all()  # type: ignore[attr-defined]
    if not users:
        click.echo("Nessun utente presente.")
        return
    for u in users:
        _echo_user(u)


# --------------------------------------------------------------------------- #
#  Create user                                                                #
# --------------------------------------------------------------------------- #
@auth_cli.command("create-user")
@click.argument("email")
@click.option("--password", "-p", help="Password in chiaro (evita prompt).")
@click.option("--admin", is_flag=True, help="Crea l’utente come amministratore.")
@with_appcontext
def create_user(email: str, password: str | None, admin: bool) -> None:
    """Crea un nuovo utente."""
    email = email.strip().lower()
    if User.query.filter_by(email=email).first():  # type: ignore[attr-defined]
        raise click.ClickException("E-mail già registrata.")

    if not password:
        password = _prompt_password()
    pwd_hash = generate_password_hash(password)

    user = User(email=email, password_hash=pwd_hash, is_admin=admin)
    db.session.add(user)
    db.session.commit()

    click.echo(click.style("✅ Utente creato:", fg="green"), nl=False)
    click.echo(f"  {email}  ({'admin' if admin else 'user'})")


# --------------------------------------------------------------------------- #
#  Set / reset password                                                       #
# --------------------------------------------------------------------------- #
@auth_cli.command("set-password")
@click.argument("email")
@click.option(
    "--random",
    is_flag=True,
    help="Genera una password casuale forte e stampala in output (no prompt).",
)
@with_appcontext
def set_password(email: str, random: bool) -> None:
    """Imposta / reimposta la password dell’utente."""
    user: User | None = User.query.filter_by(email=email.strip().lower()).first()  # type: ignore[attr-defined]
    if not user:
        raise click.ClickException("Utente non trovato.")

    if random:
        password = secrets.token_urlsafe(16)
        click.echo(f"Nuova password generata per {email}:  {click.style(password, bold=True)}")
    else:
        password = _prompt_password()

    user.password_hash = generate_password_hash(password)
    db.session.commit()
    click.echo(click.style("✅ Password aggiornata.", fg="green"))


# --------------------------------------------------------------------------- #
#  Register helper (invocato dalla factory)                                   #
# --------------------------------------------------------------------------- #
def register_cli(app) -> None:  # noqa: D401
    """Aggancia il gruppo *auth* al `flask` globale."""
    app.cli.add_command(auth_cli)
