#!/usr/bin/env python3
"""Seed di lead GHL (source_system='ghl') con storie realistiche.

Scopo
-----
Popolare la queue usata dalla pagina embed:
    /ghl-embed/assegnazioni?user_email=<sales_email>

I lead vengono creati passando da `save_sales_lead_from_ghl_payload()` (stesso
mapping del webhook /webhooks/ghl-leads/new), così da avere:
- source_system='ghl'
- form_responses/raw_payload coerenti
- sales_user_id risolto da sales_user_email (match esatto su User.email)

Uso
---
cd backend
poetry run python scripts/seed_ghl_test_leads_realistic.py --sales-email sales.duckdns@corposostenibile.com

Pulizia
-------
poetry run python scripts/seed_ghl_test_leads_realistic.py --clean

NOTE
----
- NON usa chiamate esterne.
- Scrive SOLO sul DB locale configurato da DATABASE_URL.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Permette l'import di `corposostenibile` quando eseguito da backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import func  # noqa: E402

from corposostenibile import create_app  # noqa: E402
from corposostenibile.extensions import db  # noqa: E402
from corposostenibile.models import SalesLead, User, UserRoleEnum  # noqa: E402
from corposostenibile.blueprints.sales_ghl_assignments.services import (  # noqa: E402
    save_sales_lead_from_ghl_payload,
)


DEFAULT_SALES_EMAIL = "sales.duckdns@corposostenibile.com"
DEFAULT_HM_EMAIL = "health.manager@corposostenibile.com"
SEED_EMAIL_PREFIX = "seed-ghl-"
SEED_EMAIL_DOMAIN = "example.com"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_or_create_user(email: str, *, first_name: str, last_name: str, role: UserRoleEnum) -> User:
    normalized = (email or "").strip().lower()
    if not normalized:
        raise ValueError("email vuota")

    user = User.query.filter(func.lower(User.email) == normalized).first()
    if user:
        return user

    user = User(
        email=normalized,
        password_hash="x",  # account tecnico solo per match email, NON usato per login
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_admin=False,
        is_active=True,
        is_external=(role == UserRoleEnum.team_esterno),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _build_payload(*, lead: Dict[str, Any], sales_email: str, hm_email: str) -> Dict[str, Any]:
    return {
        "event_type": "lead.created",
        "timestamp": _utc_now(),
        "opportunity": {
            "id": lead["opportunity_id"],
            "status": "new",
            "pipeline_name": "Sales Pipeline",
            "custom_fields": {
                "first_name": lead["first_name"],
                "last_name": lead["last_name"],
                "email": lead["email"],
                "telefono": lead.get("phone"),
                "sales_user_email": sales_email,
                "health_manager_email": hm_email,
                "pacchetto": lead.get("package_name"),
                "storia": lead.get("story"),
                "origin": lead.get("origin"),
                "utm_campaign": lead.get("utm_campaign"),
                "utm_medium": lead.get("utm_medium"),
                "utm_source": lead.get("utm_source"),
            },
        },
        "contact": {
            "id": lead["contact_id"],
            "name": f"{lead['first_name']} {lead['last_name']}".strip(),
            "email": lead["email"],
            "phone": lead.get("phone"),
        },
        "_seed": {
            "script": "seed_ghl_test_leads_realistic.py",
            "version": 1,
        },
    }


def _seed_leads_templates() -> List[Dict[str, Any]]:
    """Storie realistiche (mix nutrizione/coach/psicologia) per test AI criteria."""

    base = [
        {
            "slug": "chiara-postpartum",
            "first_name": "Chiara",
            "last_name": "Rinaldi",
            "phone": "+39 347 1203344",
            "origin": "Instagram Ads",
            "utm_campaign": "mamme-postpartum-apr",
            "utm_medium": "paid_social",
            "utm_source": "instagram",
            "package_name": "Premium 90 giorni",
            "story": (
                "Dopo la gravidanza (bimbo di 9 mesi) ho preso 11 kg e faccio fatica a perderli. "
                "Allatto ancora parzialmente. Ho poco tempo per cucinare, spesso salto la colazione e poi "
                "arrivo a sera con fame nervosa e mi sfogo su dolci. Dormo male e sono spesso stressata. "
                "Obiettivo: tornare in forma senza diete estreme, imparare una routine sostenibile e gestire "
                "la fame emotiva. Attività fisica: camminate 3 volte a settimana."
            ),
        },
        {
            "slug": "marco-colesterolo",
            "first_name": "Marco",
            "last_name": "De Santis",
            "phone": "+39 333 8811223",
            "origin": "Google Search",
            "utm_campaign": "colesterolo-ricerca",
            "utm_medium": "cpc",
            "utm_source": "google",
            "package_name": "Percorso Dimagrimento 90 giorni",
            "story": (
                "42 anni, lavoro d'ufficio e sto seduto molte ore. Esami del sangue con colesterolo alto "
                "e trigliceridi borderline. Ho provato a "
                "tagliare i carboidrati ma poi perdo il controllo nel weekend. Mangio spesso fuori per lavoro. "
                "Obiettivo: perdere 8-10 kg, migliorare i valori e avere un piano pratico per ristoranti/trasferte."
            ),
        },
        {
            "slug": "elena-forza",
            "first_name": "Elena",
            "last_name": "Gatti",
            "phone": "+39 349 2233445",
            "origin": "Referral",
            "utm_campaign": "passaparola-coach",
            "utm_medium": "referral",
            "utm_source": "client",
            "package_name": "Percorso Ricomposizione 90 giorni",
            "story": (
                "Mi alleno a casa con manubri ma non vedo progressi e mi manca costanza. Vorrei aumentare massa "
                "e tonificare glutei e spalle. Ho avuto un fastidio al ginocchio (rotula) e ho paura di fare squat. "
                "Disponibilità: 3 allenamenti da 45 minuti a settimana. Mi serve una programmazione chiara e "
                "supporto motivazionale."
            ),
        },
        {
            "slug": "davide-maratona",
            "first_name": "Davide",
            "last_name": "Lombardi",
            "phone": "+39 320 9988776",
            "origin": "Facebook Ads",
            "utm_campaign": "running-performance",
            "utm_medium": "paid_social",
            "utm_source": "facebook",
            "package_name": "Performance 90 giorni",
            "story": (
                "Sto preparando la mia prima mezza maratona. Corro 2 volte a settimana ma mi sento sempre "
                "scarico e recupero male. Vorrei migliorare resistenza e ritmo, e strutturare anche forza e mobilità. "
                "Lavoro su turni quindi gli orari cambiano. Ho bisogno di un piano flessibile e realistico."
            ),
        },
        {
            "slug": "francesca-binge",
            "first_name": "Francesca",
            "last_name": "Moretti",
            "phone": "+39 351 5566778",
            "origin": "TikTok Ads",
            "utm_campaign": "relazione-cibo",
            "utm_medium": "paid_social",
            "utm_source": "tiktok",
            "package_name": "N/C/P-90gg-C",
            "story": (
                "Da anni alterno periodi di dieta molto rigida a episodi di abbuffate serali. "
                "Mi sento in colpa e poi ricomincio da capo. Ansia alta e immagine corporea negativa. "
                "Ho paura di prendere peso e controllo spesso la bilancia. Vorrei lavorare sulla relazione con il cibo "
                "e sullo stress, senza fissarmi su regole estreme."
            ),
        },
        {
            "slug": "giacomo-stress",
            "first_name": "Giacomo",
            "last_name": "Pellegrini",
            "phone": "+39 342 1100223",
            "origin": "Newsletter",
            "utm_campaign": "stress-management",
            "utm_medium": "email",
            "utm_source": "newsletter",
            "package_name": "Premium 90 giorni",
            "story": (
                "37 anni, lavoro in consulenza: settimane molto intense, spesso salto i pasti e poi "
                "compenso con junk food la sera. Bevo 3-4 caffè al giorno. Sento stress cronico e fatico a "
                "staccare, anche nel weekend. Vorrei una routine più stabile e imparare a gestire emotività e fame nervosa."
            ),
        },
        {
            "slug": "martina-pcos",
            "first_name": "Martina",
            "last_name": "Serra",
            "phone": "+39 334 6677889",
            "origin": "YouTube",
            "utm_campaign": "pcos-ormoni",
            "utm_medium": "organic",
            "utm_source": "youtube",
            "package_name": "Percorso PCOS 90 giorni",
            "story": (
                "Diagnosi di PCOS, ciclo irregolare e difficoltà a perdere peso nonostante dieta e palestra. "
                "Ho gonfiore addominale e cravings per carboidrati, soprattutto nel pre-ciclo. "
                "Obiettivo: migliorare energia, composizione corporea e regolarità del ciclo con un piano nutrizionale adatto."
            ),
        },
        {
            "slug": "luca-prediabete",
            "first_name": "Luca",
            "last_name": "Vitale",
            "phone": "+39 340 9090909",
            "origin": "Meta Ads",
            "utm_campaign": "prediabete",
            "utm_medium": "paid_social",
            "utm_source": "facebook",
            "package_name": "Salute Metabolica 90 giorni",
            "story": (
                "45 anni, glicemia a digiuno alta e rischio prediabete. Ho pancia, pressione borderline e "
                "mi muovo poco. Vorrei cambiare alimentazione e iniziare ad allenarmi ma ho paura di mollare dopo 2 settimane. "
                "Ho bisogno di un percorso graduale con obiettivi chiari e supporto per la motivazione."
            ),
        },
    ]

    enriched: List[Dict[str, Any]] = []
    for idx, item in enumerate(base, start=1):
        email = f"{SEED_EMAIL_PREFIX}{idx:02d}-{item['slug']}@{SEED_EMAIL_DOMAIN}".lower()
        enriched.append(
            {
                **item,
                "email": email,
                "opportunity_id": f"opp_seed_{idx:02d}",
                "contact_id": f"contact_seed_{idx:02d}",
            }
        )
    return enriched


def seed(*, sales_email: str, hm_email: str, clean: bool) -> int:
    app = create_app()

    with app.app_context():
        if clean:
            deleted = SalesLead.query.filter(
                SalesLead.source_system == "ghl",
                SalesLead.email.ilike(f"{SEED_EMAIL_PREFIX}%@{SEED_EMAIL_DOMAIN}"),
            ).delete(synchronize_session=False)
            db.session.commit()
            print(f"Rimossi {deleted} SalesLead seed (source_system='ghl').")
            return 0

        sales_user = _get_or_create_user(
            sales_email,
            first_name="Sales",
            last_name="DuckDNS",
            role=UserRoleEnum.team_esterno,
        )
        hm_user = _get_or_create_user(
            hm_email,
            first_name="Health",
            last_name="Manager",
            role=UserRoleEnum.health_manager,
        )
        db.session.commit()

        print(f"Sales user per scope JWT: {sales_user.full_name} <{sales_user.email}> (id={sales_user.id})")
        print(f"Health manager: {hm_user.full_name} <{hm_user.email}> (id={hm_user.id})")

        leads = _seed_leads_templates()

        created = 0
        updated = 0
        for lead in leads:
            payload = _build_payload(lead=lead, sales_email=sales_user.email, hm_email=hm_user.email)
            saved, was_created = save_sales_lead_from_ghl_payload(payload, "127.0.0.1")
            if was_created:
                created += 1
            else:
                updated += 1
            print(
                f"  [{'CREATED' if was_created else 'UPDATED'}] lead_id={saved.id} "
                f"{saved.first_name} {saved.last_name} <{saved.email}>"
            )

        print(f"\nDone: {created} creati, {updated} aggiornati.")
        print("\nApri la pagina embed:")
        print(f"  /ghl-embed/assegnazioni?user_email={sales_user.email}")
        print("\nSuggerimento: per test AI reale, assicurati di avere GOOGLE_API_KEY settata nell'ambiente del backend.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sales-email", default=DEFAULT_SALES_EMAIL)
    parser.add_argument("--hm-email", default=DEFAULT_HM_EMAIL)
    parser.add_argument("--clean", action="store_true")

    args = parser.parse_args()
    return seed(sales_email=args.sales_email, hm_email=args.hm_email, clean=args.clean)


if __name__ == "__main__":
    raise SystemExit(main())
