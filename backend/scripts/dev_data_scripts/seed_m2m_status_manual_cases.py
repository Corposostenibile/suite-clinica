#!/usr/bin/env python3
"""
Seed non distruttivo per creare casi manuali M2M sugli stati cliente.

Obiettivo:
- Creare/aggiornare pochi clienti "M2M TEST - ..." facili da cercare in UI.
- Assegnare professionisti via relazioni many-to-many (e FK legacy allineate).
- Impostare stati servizio per verificare regole globali:
  * se almeno un servizio assegnato è attivo -> globale attivo
  * se tutti i servizi assegnati sono ghost -> globale ghost
  * se tutti i servizi assegnati sono pausa -> globale pausa

Uso:
  poetry run python scripts/dev_data_scripts/seed_m2m_status_manual_cases.py --apply
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class CaseDefinition:
    key: str
    display_name: str
    services: tuple[str, ...]  # nutrizione | coach | psicologia
    stato_nutrizione: str | None
    stato_coach: str | None
    stato_psicologia: str | None
    expected_global: str


CASES: tuple[CaseDefinition, ...] = (
    CaseDefinition(
        key="ALL_GHOST",
        display_name="M2M TEST - Tutti Ghost",
        services=("nutrizione", "coach"),
        stato_nutrizione="ghost",
        stato_coach="ghost",
        stato_psicologia=None,
        expected_global="ghost",
    ),
    CaseDefinition(
        key="MIX_ACTIVE_GHOST",
        display_name="M2M TEST - Mix Attivo Ghost",
        services=("nutrizione", "coach"),
        stato_nutrizione="attivo",
        stato_coach="ghost",
        stato_psicologia=None,
        expected_global="attivo",
    ),
    CaseDefinition(
        key="ALL_PAUSA",
        display_name="M2M TEST - Tutti Pausa",
        services=("nutrizione", "coach"),
        stato_nutrizione="pausa",
        stato_coach="pausa",
        stato_psicologia=None,
        expected_global="pausa",
    ),
    CaseDefinition(
        key="THREE_SERVICES_MIX",
        display_name="M2M TEST - 3 Servizi Mix",
        services=("nutrizione", "coach", "psicologia"),
        stato_nutrizione="ghost",
        stato_coach="attivo",
        stato_psicologia="ghost",
        expected_global="attivo",
    ),
)


def _programma_from_services(services: tuple[str, ...]) -> str:
    mapping = {
        frozenset({"nutrizione"}): "N",
        frozenset({"coach"}): "C",
        frozenset({"psicologia"}): "P",
        frozenset({"nutrizione", "coach"}): "N+C",
        frozenset({"nutrizione", "psicologia"}): "N+P",
        frozenset({"coach", "psicologia"}): "C+P",
        frozenset({"nutrizione", "coach", "psicologia"}): "N+C+P",
    }
    return mapping[frozenset(services)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed casi manuali M2M stato cliente")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica modifiche a DB (senza questo flag non scrive nulla).",
    )
    args = parser.parse_args()

    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import (
        Cliente,
        ClienteProfessionistaHistory,
        StatoClienteEnum,
        User,
        UserSpecialtyEnum,
    )

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("SEED MANUALE M2M - STATI GLOBALI CLIENTE")
        print("=" * 70)
        if not args.apply:
            print("Modalita DRY-RUN: nessuna modifica verra salvata.")

        nutrizionista = (
            User.query.filter(
                User.specialty == UserSpecialtyEnum.nutrizionista,
                User.is_active.is_(True),
            )
            .order_by(User.id.asc())
            .first()
        )
        coach = (
            User.query.filter(
                User.specialty == UserSpecialtyEnum.coach,
                User.is_active.is_(True),
            )
            .order_by(User.id.asc())
            .first()
        )
        psicologo = (
            User.query.filter(
                User.specialty == UserSpecialtyEnum.psicologo,
                User.is_active.is_(True),
            )
            .order_by(User.id.asc())
            .first()
        )
        admin = User.query.filter(User.is_admin.is_(True)).order_by(User.id.asc()).first()

        missing = []
        if not nutrizionista:
            missing.append("nutrizionista")
        if not coach:
            missing.append("coach")
        if not psicologo:
            missing.append("psicologo")
        if not admin:
            missing.append("admin")
        if missing:
            print(f"ERRORE: ruoli mancanti per seed -> {', '.join(missing)}")
            return

        print(
            f"Professionisti usati: nutrizionista={nutrizionista.id}, "
            f"coach={coach.id}, psicologo={psicologo.id}, admin={admin.id}"
        )

        created = 0
        updated = 0
        today = date.today()

        for idx, case in enumerate(CASES, start=1):
            email = f"m2m.test.{idx:02d}@example.local"
            cliente = Cliente.query.filter_by(mail=email).first()
            is_new = cliente is None

            if is_new:
                cliente = Cliente(
                    nome_cognome=case.display_name,
                    mail=email,
                    genere="donna",
                    numero_telefono=f"+39 320 0000{idx:03d}",
                    professione="QA M2M",
                    paese="Italia",
                    data_inizio_abbonamento=today,
                )
                db.session.add(cliente)
                if args.apply:
                    db.session.flush()
                created += 1
            else:
                cliente.nome_cognome = case.display_name
                updated += 1

            # Allinea programma e reset assegnazioni
            cliente.programma_attuale = _programma_from_services(case.services)
            cliente.nutrizionisti_multipli = []
            cliente.coaches_multipli = []
            cliente.psicologi_multipli = []
            cliente.nutrizionista_id = None
            cliente.coach_id = None
            cliente.psicologa_id = None

            # Assegna professionisti in base ai servizi del caso
            if "nutrizione" in case.services:
                cliente.nutrizionisti_multipli = [nutrizionista]
                cliente.nutrizionista_id = nutrizionista.id
            if "coach" in case.services:
                cliente.coaches_multipli = [coach]
                cliente.coach_id = coach.id
            if "psicologia" in case.services:
                cliente.psicologi_multipli = [psicologo]
                cliente.psicologa_id = psicologo.id

            # Stati servizio + chat allineati
            cliente.stato_nutrizione = (
                StatoClienteEnum(case.stato_nutrizione) if case.stato_nutrizione else None
            )
            cliente.stato_coach = StatoClienteEnum(case.stato_coach) if case.stato_coach else None
            cliente.stato_psicologia = (
                StatoClienteEnum(case.stato_psicologia) if case.stato_psicologia else None
            )
            cliente.stato_cliente_chat_nutrizione = cliente.stato_nutrizione
            cliente.stato_cliente_chat_coaching = cliente.stato_coach
            cliente.stato_cliente_chat_psicologia = cliente.stato_psicologia

            # Imposta stato globale coerente con aspettativa del caso
            cliente.stato_cliente = StatoClienteEnum(case.expected_global)
            cliente.stato_cliente_data = datetime.utcnow()

            if args.apply:
                # Rendi leggibile anche lo storico assegnazioni nella tab Team
                ClienteProfessionistaHistory.query.filter_by(
                    cliente_id=cliente.cliente_id, is_active=True
                ).update({"is_active": False}, synchronize_session=False)

                for tipo, user in (
                    ("nutrizionista", nutrizionista if "nutrizione" in case.services else None),
                    ("coach", coach if "coach" in case.services else None),
                    ("psicologa", psicologo if "psicologia" in case.services else None),
                ):
                    if user is None:
                        continue
                    db.session.add(
                        ClienteProfessionistaHistory(
                            cliente_id=cliente.cliente_id,
                            user_id=user.id,
                            tipo_professionista=tipo,
                            data_dal=today,
                            motivazione_aggiunta=f"Seed manuale M2M {case.key}",
                            assegnato_da_id=admin.id,
                            is_active=True,
                        )
                    )

            print(
                f"[{case.key}] {case.display_name} | servizi={','.join(case.services)} | "
                f"stati=(N:{case.stato_nutrizione}, C:{case.stato_coach}, P:{case.stato_psicologia}) | "
                f"globale_atteso={case.expected_global} | email={email}"
            )

        if args.apply:
            db.session.commit()
            print("-" * 70)
            print(f"Completato: creati={created}, aggiornati={updated}")
            print("Clienti seed pronti per test manuali in UI.")
        else:
            db.session.rollback()
            print("-" * 70)
            print("Dry-run completato: nessuna modifica salvata.")


if __name__ == "__main__":
    main()
