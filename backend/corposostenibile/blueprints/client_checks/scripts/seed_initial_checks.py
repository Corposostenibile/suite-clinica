#!/usr/bin/env python3
"""
Seed idempotente dei check iniziali usati dal bridge GHL.

Crea/aggiorna:
1) Check 1 - PRE-CHECK INIZIALE (derivato dal PDF PRE-CHECK INIZIALE.pdf)
2) Check 2 - Mockup Follow-up Iniziale (placeholder temporaneo)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[4]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    CheckForm,
    CheckFormField,
    CheckFormFieldTypeEnum,
    CheckFormTypeEnum,
    User,
)


CHECK_1_FIELDS: list[dict[str, Any]] = [
    # 1. DATI GENERALI
    {"label": "Foto recente frontale (facoltativa)", "field_type": "file", "is_required": False},
    {"label": "Foto recente laterale (facoltativa)", "field_type": "file", "is_required": False},
    {"label": "Foto recente posteriore (facoltativa)", "field_type": "file", "is_required": False},
    {"label": "Data di nascita", "field_type": "date", "is_required": True},
    {"label": "Altezza (cm) - se te la senti", "field_type": "number", "is_required": False},
    {"label": "Peso (kg) - se te la senti", "field_type": "number", "is_required": False},
    {"label": "Data dell'ultimo peso", "field_type": "date", "is_required": False},
    {"label": "Se preferisci non indicarlo, raccontaci brevemente il perche'", "field_type": "textarea", "is_required": False},

    # 2. ANALISI CLINICHE E STATO DI SALUTE
    {"label": "Hai effettuato delle analisi del sangue negli ultimi 6 mesi?", "field_type": "radio", "is_required": True, "options": {"choices": ["Si (allegare)", "No"]}},
    {"label": "Allega analisi del sangue recenti", "field_type": "file", "is_required": False},
    {"label": "Patologie diagnosticate - Gastrointestinali", "field_type": "multiselect", "is_required": False, "options": {"choices": ["IBS", "Reflusso", "Gastrite", "Diverticolite", "Morbo di Crohn"]}},
    {"label": "Patologie diagnosticate - Metaboliche / Endocrine", "field_type": "multiselect", "is_required": False, "options": {"choices": ["Insulino-resistenza", "Diabete tipo 1", "Diabete tipo 2", "Dislipidemia", "Steatosi epatica", "Ipotiroidismo", "Ipertiroidismo"]}},
    {"label": "Altre problematiche ormonali (specificare)", "field_type": "textarea", "is_required": False},
    {"label": "Patologie diagnosticate - Ginecologiche", "field_type": "multiselect", "is_required": False, "options": {"choices": ["PCOS", "Endometriosi", "Menopausa"]}},
    {"label": "Patologie diagnosticate - Altre", "field_type": "multiselect", "is_required": False, "options": {"choices": ["Ipertensione", "Osteoporosi", "Patologie renali", "Cure oncologiche (attuali o pregresse)", "Epilessia", "Artrosi", "Fibromialgia", "Sclerosi multipla", "Lipedema", "Problematiche cutanee", "Malattie metaboliche ereditarie"]}},
    {"label": "Patologie renali - quali?", "field_type": "textarea", "is_required": False},
    {"label": "Malattie metaboliche ereditarie - quali?", "field_type": "textarea", "is_required": False},
    {"label": "Altre patologie non sopra riportate", "field_type": "textarea", "is_required": False},

    # 3. ALLERGIE, INTOLLERANZE, FARMACI
    {"label": "Allergie alimentari?", "field_type": "radio", "is_required": True, "options": {"choices": ["Si", "No"]}},
    {"label": "Allergie alimentari - quali?", "field_type": "textarea", "is_required": False},
    {"label": "Intolleranze?", "field_type": "radio", "is_required": True, "options": {"choices": ["Si", "No"]}},
    {"label": "Intolleranze - quali?", "field_type": "textarea", "is_required": False},

    # 4. FARMACI
    {"label": "Assumi regolarmente farmaci o integratori?", "field_type": "radio", "is_required": True, "options": {"choices": ["Si", "No"]}},
    {"label": "Se si, specifica farmaci/integratori e dosaggi (se noti)", "field_type": "textarea", "is_required": False},

    # 5. OBIETTIVI
    {"label": "Qual e' il tuo obiettivo principale in questo momento?", "field_type": "select", "is_required": True, "options": {"choices": ["Dimagrire (perdita di massa grassa)", "Tonificare (ricomposizione corporea)", "Migliorare digestione", "Aumento del tono muscolare", "Lavorare insieme sul rapporto col cibo", "Altro"]}},
    {"label": "Obiettivo principale - altro (specifica)", "field_type": "textarea", "is_required": False},
    {"label": "Cosa vorresti ottenere nelle prime 8 settimane di questo Percorso?", "field_type": "textarea", "is_required": True},
    {"label": "Qual e' il tuo obiettivo a lungo termine di questo Percorso (12 mesi)?", "field_type": "textarea", "is_required": True},

    # 6. STORIA ALIMENTARE
    {"label": "Come descriveresti la tua alimentazione attuale?", "field_type": "select", "is_required": True, "options": {"choices": ["Onnivora", "Vegetariana", "Vegana", "Digiuno intermittente", "Chetogenica", "Altro"]}},
    {"label": "Alimentazione attuale - altro (specifica)", "field_type": "textarea", "is_required": False},
    {"label": "Hai seguito in passato regimi alimentari specifici?", "field_type": "radio", "is_required": True, "options": {"choices": ["Si", "No"]}},
    {"label": "Se si, descrivili brevemente", "field_type": "textarea", "is_required": False},
    {"label": "Allega eventuale piano alimentare seguito in passato (facoltativo)", "field_type": "file", "is_required": False},

    # 7. RECALL 24H - GIORNATA TIPO
    {"label": "Colazione - ora - cosa - quanto", "field_type": "textarea", "is_required": False},
    {"label": "Spuntino - ora - cosa - quanto", "field_type": "textarea", "is_required": False},
    {"label": "Pranzo - ora - cosa - quanto", "field_type": "textarea", "is_required": False},
    {"label": "Merenda - ora - cosa - quanto", "field_type": "textarea", "is_required": False},
    {"label": "Cena - ora - cosa - quanto", "field_type": "textarea", "is_required": False},
    {"label": "Pre-nanna - ora - cosa - quanto", "field_type": "textarea", "is_required": False},
    {"label": "Hai esigenze specifiche su numero/orari dei pasti? (lavoro, allenamenti, fame, digestione, preferenze...)", "field_type": "textarea", "is_required": False},

    # 8. RELAZIONE CON IL CIBO, DIGESTIONE, IDRATAZIONE, INTESTINO
    {"label": "Alimenti che ti piacciono molto (lista)", "field_type": "textarea", "is_required": False},
    {"label": "Alimenti che non ti piacciono (lista)", "field_type": "textarea", "is_required": False},
    {"label": "Quanto alcol consumi settimanalmente?", "field_type": "select", "is_required": True, "options": {"choices": ["Mai", "Raramente", "1-3 porzioni", "4-6 porzioni", "> 6 porzioni"]}},
    {"label": "Quanta acqua bevi mediamente al giorno?", "field_type": "select", "is_required": True, "options": {"choices": ["< 1 L / meno di 5 bicchieri", "1-1.5 L / dai 5 ai 7 bicchieri", "1.5-2 L / dai 7 ai 10 bicchieri", "> 2 L / piu' di 10 bicchieri"]}},
    {"label": "Bevi altre bevande durante il giorno? Se si quali e in che quantita'?", "field_type": "textarea", "is_required": False},
    {"label": "Valuta la tua digestione (1 = pessima / 5 = ottima)", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "Commenti digestione", "field_type": "textarea", "is_required": False},
    {"label": "Regolarita' intestinale", "field_type": "select", "is_required": True, "options": {"choices": ["< 2 volte/settimana", "2-5 volte/settimana", "Tutti i giorni", "Piu' volte al giorno"]}},

    # 9. SONNO E STILE DI VITA
    {"label": "Ore di sonno per notte", "field_type": "select", "is_required": True, "options": {"choices": ["< 6", "6-8", "> 8"]}},
    {"label": "Orario medio di sveglia", "field_type": "text", "is_required": False},
    {"label": "Orario medio di addormentamento", "field_type": "text", "is_required": False},
    {"label": "Qualita' del sonno (1-5)", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},

    # 10. ATTIVITA' FISICA
    {"label": "Sei uno sportivo agonista?", "field_type": "radio", "is_required": True, "options": {"choices": ["Si", "No"]}},
    {"label": "Se si, sport", "field_type": "text", "is_required": False},
    {"label": "Frequenza allenamenti", "field_type": "select", "is_required": True, "options": {"choices": ["Piu' volte al giorno", "Tutti i giorni", "3-5 volte a settimana", "< 3 volte a settimana"]}},
    {"label": "Storico sportivo e sessioni tipo", "field_type": "textarea", "is_required": False},

    # 11. APPROCCIO E MINDSET
    {"label": "In questa fase preferisci una routine alimentare", "field_type": "radio", "is_required": True, "options": {"choices": ["Piu' strutturata e rigida", "Piu' flessibile"]}},
    {"label": "Come mai credi che questo approccio sia il piu' funzionale per te?", "field_type": "textarea", "is_required": False},
    {"label": "Secondo te, cosa ti ha impedito finora di ottenere i risultati che desideravi?", "field_type": "textarea", "is_required": False},
    {"label": "Se hai gia' fallito in passato, cosa senti che e' diverso questa volta?", "field_type": "textarea", "is_required": False},
    {"label": "Come immagini il tuo successo tra 1 anno (peso, relazione col cibo, energia, abitudini, relazioni, mindset)", "field_type": "textarea", "is_required": False},
    {"label": "Hai avuto esitazioni nel richiedere/investire nel Percorso 1to1? Se si, come mai?", "field_type": "textarea", "is_required": False},

    # 12. STORICO FISIOLOGICO
    {"label": "Indica se hai mai riportato infortuni di qualsiasi tipo", "field_type": "textarea", "is_required": False},
    {"label": "Hai una o piu' di queste patologie?", "field_type": "multiselect", "is_required": False, "options": {"choices": ["Ipertensione", "Artrite", "Artrosi", "Asma", "Osteoporosi", "Fibromialgia", "Altre patologie non indicate sopra"]}},
    {"label": "Altre patologie non indicate sopra - specifica", "field_type": "textarea", "is_required": False},
    {"label": "Hai uno o piu' dei seguenti dolori?", "field_type": "multiselect", "is_required": False, "options": {"choices": ["Dolore alla schiena", "Dolore alla cervicale", "Dolore alle ginocchia", "Dolore ai polsi", "Dolore alle spalle"]}},

    # PROFILO PERSONOLOGICO (10 domande)
    {"label": "[Collaborativo] 1) Quando mi sento confuso o in difficolta', cerco di capire cosa posso cambiare nella mia vita.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Collaborativo] 2) Quando decido di affrontare un cambiamento, riesco a portare avanti l'impegno anche nei momenti difficili.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Difensivo e diffidente] 3) A volte tendo a trattenere o non condividere le mie difficolta', anche quando qualcuno mi offre ascolto.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Difensivo e diffidente] 4) A volte ho la sensazione che gli altri non possano davvero capire cosa provo, anche se provo a spiegarmi.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Passivo e dipendente] 5) In certe situazioni mi sento piu' tranquillo quando qualcun altro prende decisioni per me.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Passivo e dipendente] 6) In alcune situazioni, preferisco che le persone capiscano da sole come sto, piuttosto che parlarne apertamente.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Ambivalente e instabile] 7) Mi succede che il mio umore cambi velocemente, anche senza un motivo preciso.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Ambivalente e instabile] 8) Mi e' capitato di iniziare qualcosa con entusiasmo e poi perdere motivazione prima della fine.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Distaccato e razionale] 9) In alcuni momenti, quando provo disagio, tendo a guardare le situazioni con distacco.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
    {"label": "[Distaccato e razionale] 10) A volte non mi piace che qualcuno cerchi di farmi parlare troppo delle mie emozioni.", "field_type": "scale", "is_required": True, "options": {"min": 1, "max": 5}},
]


CHECK_2_MOCKUP_FIELDS: list[dict[str, Any]] = [
    {
        "label": "Come valuti la tua settimana (1-5)?",
        "field_type": "scale",
        "is_required": True,
        "options": {"min": 1, "max": 5},
    },
    {
        "label": "Aderenza al piano (0-100%)",
        "field_type": "number",
        "is_required": True,
        "placeholder": "es. 80",
    },
    {
        "label": "Energia media percepita",
        "field_type": "select",
        "is_required": True,
        "options": {"choices": ["Bassa", "Media", "Alta"]},
    },
    {"label": "Difficolta' principali della settimana", "field_type": "textarea", "is_required": False},
    {"label": "Domande per il team", "field_type": "textarea", "is_required": False},
]


FORMS_DEFINITION: list[dict[str, Any]] = [
    {
        "name": "Check 1 - PRE-CHECK INIZIALE",
        "description": "Derivato dal documento PRE-CHECK INIZIALE.pdf.",
        "fields": CHECK_1_FIELDS,
    },
    {
        "name": "Check 2 - Mockup Follow-up Iniziale",
        "description": "Mockup temporaneo in attesa del secondo questionario definitivo.",
        "fields": CHECK_2_MOCKUP_FIELDS,
    },
]


def _resolve_creator_user_id() -> int:
    admin_user = User.query.filter_by(is_admin=True).first()
    if admin_user:
        return admin_user.id

    fallback_user = User.query.first()
    if fallback_user:
        return fallback_user.id

    raise RuntimeError("Nessun utente disponibile: crea prima un utente admin.")


def _replace_fields(form: CheckForm, fields_data: list[dict[str, Any]]) -> None:
    CheckFormField.query.filter_by(form_id=form.id).delete()
    db.session.flush()

    for position, field_data in enumerate(fields_data, start=1):
        field = CheckFormField(
            form_id=form.id,
            label=field_data["label"],
            field_type=CheckFormFieldTypeEnum(field_data["field_type"]),
            is_required=bool(field_data.get("is_required", False)),
            position=position,
            options=field_data.get("options"),
            placeholder=field_data.get("placeholder"),
            help_text=field_data.get("help_text"),
        )
        db.session.add(field)


def seed_initial_checks() -> None:
    creator_user_id = _resolve_creator_user_id()

    for form_def in FORMS_DEFINITION:
        form = CheckForm.query.filter_by(
            name=form_def["name"],
            form_type=CheckFormTypeEnum.iniziale,
        ).first()

        if not form:
            form = CheckForm(
                name=form_def["name"],
                description=form_def["description"],
                form_type=CheckFormTypeEnum.iniziale,
                is_active=True,
                created_by_id=creator_user_id,
                department_id=None,
            )
            db.session.add(form)
            db.session.flush()
            print(f"[seed_initial_checks] Creato form: {form.name} (id={form.id})")
        else:
            form.description = form_def["description"]
            form.is_active = True
            if not form.created_by_id:
                form.created_by_id = creator_user_id
            print(f"[seed_initial_checks] Aggiornamento form: {form.name} (id={form.id})")

        _replace_fields(form, form_def["fields"])
        print(f"[seed_initial_checks] -> campi impostati: {len(form_def['fields'])}")

    db.session.commit()
    print("[seed_initial_checks] Seed completato con successo.")


def main() -> int:
    app = create_app()
    with app.app_context():
        try:
            seed_initial_checks()
            return 0
        except Exception as exc:
            db.session.rollback()
            print(f"[seed_initial_checks] Errore: {exc}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
