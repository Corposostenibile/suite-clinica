#!/usr/bin/env python3
"""
Script per inviare (o ri-inviare) l'email di riepilogo check settimanale al cliente.

Utile per testare l'email di riepilogo senza compilare di nuovo il check:
- senza argomenti: usa l'ultima WeeklyCheckResponse nel DB
- con response_id: invia il riepilogo per quella risposta specifica

Requisiti: il cliente associato deve avere mail valorizzato (cliente.mail).

Usage (dalla cartella backend):
    poetry run python scripts/send_weekly_check_summary_email.py
    poetry run python scripts/send_weekly_check_summary_email.py 42
"""
import sys
import os

# Root progetto (backend) in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import WeeklyCheckResponse
from corposostenibile.blueprints.client_checks.services import NotificationService


def main():
    response_id = None
    if len(sys.argv) > 1:
        try:
            response_id = int(sys.argv[1])
        except ValueError:
            print("Errore: response_id deve essere un intero.")
            sys.exit(1)

    app = create_app()
    with app.app_context():
        if response_id:
            response = db.session.get(WeeklyCheckResponse, response_id)
            if not response:
                print(f"Nessuna WeeklyCheckResponse con id={response_id}.")
                sys.exit(1)
        else:
            response = (
                WeeklyCheckResponse.query
                .order_by(WeeklyCheckResponse.submit_date.desc())
                .first()
            )
            if not response:
                print("Nessuna WeeklyCheckResponse nel database.")
                sys.exit(1)
            response_id = response.id

        cliente = response.assignment.cliente if response.assignment else None
        if not cliente:
            print(f"Response {response_id} senza assignment/cliente.")
            sys.exit(1)
        mail = getattr(cliente, "mail", None)
        if not mail or not str(mail).strip():
            print(
                f"Cliente {cliente.nome_cognome} (id={cliente.cliente_id}) non ha mail valorizzato. "
                "Impossibile inviare l'email."
            )
            sys.exit(1)

        print(
            f"Invio email riepilogo per response_id={response_id} "
            f"(cliente={cliente.nome_cognome}, mail={mail})..."
        )
        try:
            NotificationService.send_weekly_check_summary_to_client(response)
            print("Email inviata con successo.")
        except Exception as e:
            print(f"Errore durante l'invio: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
