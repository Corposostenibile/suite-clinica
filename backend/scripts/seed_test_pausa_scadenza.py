#!/usr/bin/env python3
"""
Crea clienti di test per verificare l'estensione della data di scadenza
alla riattivazione da pausa.

Oggi di riferimento: 12/02/2026.
Per ogni cliente:
- Stato servizio = Pausa
- Data inizio pausa (stato_*_data) = 5 giorni fa (07/02/2026)
- Data scadenza piano = 20/02/2026

Quando in UI riattivi il paziente (stato → Attivo), la logica deve estendere
la scadenza di 5 giorni → nuova data 25/02/2026.

Uso:
  cd backend && poetry run python scripts/seed_test_pausa_scadenza.py

Requisiti: almeno un nutrizionista e un coach in DB (es. dopo seed_test_data.py).
"""

import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OGGI = date(2026, 2, 12)
PAUSA_DAYS_AGO = 5
DATA_INIZIO_PAUSA = OGGI - timedelta(days=PAUSA_DAYS_AGO)  # 07/02/2026
DATA_SCADENZA_PRIMA = OGGI + timedelta(days=8)              # 20/02/2026
DATA_SCADENZA_DOPO = DATA_SCADENZA_PRIMA + timedelta(days=PAUSA_DAYS_AGO)  # 25/02/2026


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, User, StatoClienteEnum, UserSpecialtyEnum, StatoServizioLog

    app = create_app()
    with app.app_context():
        nutrizionista = User.query.filter(
            User.specialty.in_([UserSpecialtyEnum.nutrizionista, UserSpecialtyEnum.nutrizione])
        ).filter_by(is_active=True).first()
        coach = User.query.filter_by(specialty=UserSpecialtyEnum.coach, is_active=True).first()

        if not nutrizionista or not coach:
            print("⚠️  Servono almeno un nutrizionista e un coach in DB.")
            print("   Esegui prima: poetry run python scripts/seed_test_data.py")
            sys.exit(1)

        # Evita duplicati: rimuovi eventuali clienti "Test Scadenza Pausa" precedenti
        esistenti = Cliente.query.filter(
            Cliente.nome_cognome.like("Test Scadenza Pausa%")
        ).all()
        if esistenti:
            ids = [c.cliente_id for c in esistenti]
            # Rimuovi prima lo storico stati servizio (evita UPDATE cliente_id=NULL su delete)
            deleted_logs = StatoServizioLog.query.filter(StatoServizioLog.cliente_id.in_(ids)).delete(synchronize_session=False)
            for c in esistenti:
                db.session.delete(c)
            db.session.commit()
            print(f"   Rimossi {len(esistenti)} clienti di test e {deleted_logs} record storico stati.")

        pausa_datetime = datetime.combine(DATA_INIZIO_PAUSA, datetime.min.time())

        # 1) Solo nutrizione in pausa
        c1 = Cliente(
            nome_cognome="Test Scadenza Pausa - Nutrizione",
            mail="test.pausa.nutrizione@test.local",
            data_di_nascita=date(1990, 5, 15),
            genere="donna",
            numero_telefono="+39 333 1110001",
            indirizzo="Via Test 1, Milano",
            professione="Impiegata",
            paese="Italia",
            tipologia_cliente="a",
            stato_cliente=StatoClienteEnum.pausa,
            programma_attuale="3 mesi",
            data_inizio_abbonamento=OGGI - timedelta(days=60),
            durata_programma_giorni=90,
            data_rinnovo=DATA_SCADENZA_PRIMA,
            nutrizionista_id=nutrizionista.id,
            coach_id=None,
            psicologa_id=None,
            stato_nutrizione=StatoClienteEnum.pausa,
            stato_nutrizione_data=pausa_datetime,
            stato_coach=None,
            stato_coach_data=None,
            stato_psicologia=None,
            stato_psicologia_data=None,
            data_scadenza_nutrizione=DATA_SCADENZA_PRIMA,
            data_scadenza_coach=None,
            data_scadenza_psicologia=None,
        )
        db.session.add(c1)

        # 2) Solo coach in pausa
        c2 = Cliente(
            nome_cognome="Test Scadenza Pausa - Coach",
            mail="test.pausa.coach@test.local",
            data_di_nascita=date(1985, 8, 20),
            genere="uomo",
            numero_telefono="+39 333 1110002",
            indirizzo="Via Test 2, Roma",
            professione="Libero professionista",
            paese="Italia",
            tipologia_cliente="b",
            stato_cliente=StatoClienteEnum.pausa,
            programma_attuale="6 mesi",
            data_inizio_abbonamento=OGGI - timedelta(days=120),
            durata_programma_giorni=180,
            data_rinnovo=DATA_SCADENZA_PRIMA,
            nutrizionista_id=None,
            coach_id=coach.id,
            psicologa_id=None,
            stato_nutrizione=None,
            stato_nutrizione_data=None,
            stato_coach=StatoClienteEnum.pausa,
            stato_coach_data=pausa_datetime,
            stato_psicologia=None,
            stato_psicologia_data=None,
            data_scadenza_nutrizione=None,
            data_scadenza_coach=DATA_SCADENZA_PRIMA,
            data_scadenza_psicologia=None,
        )
        db.session.add(c2)

        # 3) Nutrizione + Coach entrambi in pausa (due scadenze da estendere)
        c3 = Cliente(
            nome_cognome="Test Scadenza Pausa - Multi",
            mail="test.pausa.multi@test.local",
            data_di_nascita=date(1988, 3, 10),
            genere="donna",
            numero_telefono="+39 333 1110003",
            indirizzo="Via Test 3, Napoli",
            professione="Manager",
            paese="Italia",
            tipologia_cliente="a",
            stato_cliente=StatoClienteEnum.pausa,
            programma_attuale="12 mesi",
            data_inizio_abbonamento=OGGI - timedelta(days=200),
            durata_programma_giorni=365,
            data_rinnovo=DATA_SCADENZA_PRIMA,
            nutrizionista_id=nutrizionista.id,
            coach_id=coach.id,
            psicologa_id=None,
            stato_nutrizione=StatoClienteEnum.pausa,
            stato_nutrizione_data=pausa_datetime,
            stato_coach=StatoClienteEnum.pausa,
            stato_coach_data=pausa_datetime,
            stato_psicologia=None,
            stato_psicologia_data=None,
            data_scadenza_nutrizione=DATA_SCADENZA_PRIMA,
            data_scadenza_coach=DATA_SCADENZA_PRIMA,
            data_scadenza_psicologia=None,
        )
        db.session.add(c3)

        db.session.commit()

        print("=" * 60)
        print("CLIENTI TEST PAUSA → ESTENSIONE SCADENZA")
        print("=" * 60)
        print(f"Oggi di riferimento: {OGGI}")
        print(f"Data inizio pausa (stato_*_data): {DATA_INIZIO_PAUSA} ({PAUSA_DAYS_AGO} giorni fa)")
        print(f"Scadenza attuale: {DATA_SCADENZA_PRIMA}")
        print(f"Dopo riattivazione (attesa): {DATA_SCADENZA_DOPO} (+{PAUSA_DAYS_AGO} giorni)")
        print()
        print("Creati 3 clienti (cerca 'Test Scadenza Pausa' in lista pazienti):")
        print("  1. Test Scadenza Pausa - Nutrizione  (solo nutrizione in pausa)")
        print("  2. Test Scadenza Pausa - Coach       (solo coach in pausa)")
        print("  3. Test Scadenza Pausa - Multi     (nutrizione + coach in pausa)")
        print()
        print("Prova: in UI passa lo stato da 'Pausa' ad 'Attivo' e verifica che")
        print("       data_scadenza_nutrizione / data_scadenza_coach diventi il 25/02/2026.")
        print("=" * 60)


if __name__ == "__main__":
    main()
