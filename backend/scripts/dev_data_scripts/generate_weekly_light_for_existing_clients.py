"""
Script retroattivo: genera WeeklyCheckLight per tutti i clienti esistenti
che non ne hanno ancora uno.

Esegui una volta sola con:
    flask shell < scripts/dev_data_scripts/generate_weekly_light_for_existing_clients.py
oppure:
    python scripts/dev_data_scripts/generate_weekly_light_for_existing_clients.py

Richiede il contesto Flask attivo.
"""
import secrets
import sys

from corposostenibile.extensions import db
from corposostenibile.models import Cliente, WeeklyCheckLight


def run():
    clienti_senza_light = (
        db.session.query(Cliente)
        .outerjoin(WeeklyCheckLight, WeeklyCheckLight.cliente_id == Cliente.cliente_id)
        .filter(WeeklyCheckLight.id.is_(None))
        .all()
    )

    total = len(clienti_senza_light)
    print(f"Clienti senza WeeklyCheckLight: {total}")

    if total == 0:
        print("Nessun cliente da aggiornare.")
        return

    created = 0
    for cliente in clienti_senza_light:
        try:
            light = WeeklyCheckLight(
                cliente_id=cliente.cliente_id,
                token=secrets.token_urlsafe(32),
                is_active=True,
            )
            db.session.add(light)
            created += 1
        except Exception as e:
            print(f"  Errore cliente {cliente.cliente_id}: {e}")

    db.session.commit()
    print(f"WeeklyCheckLight creati: {created}/{total}")


if __name__ == '__main__':
    # Esecuzione diretta (richiede FLASK_APP configurato)
    try:
        from corposostenibile import create_app
        app = create_app()
        with app.app_context():
            run()
    except ImportError as e:
        print(f"Errore import: {e}")
        print("Esegui dallo shell Flask: flask shell < questo_script.py")
        sys.exit(1)
else:
    # Eseguito dentro flask shell
    run()
