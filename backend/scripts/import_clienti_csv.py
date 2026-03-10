#!/usr/bin/env python3
"""
Import clienti dal CSV esportato (clienti_dal_2_marzo_2026.csv).

Uso:
    # Dry-run (verifica senza scrivere nel DB)
    flask run-script import-clienti /path/to/file.csv --dry-run

    # Import effettivo
    flask run-script import-clienti /path/to/file.csv

    # Oppure standalone (con app context):
    python scripts/import_clienti_csv.py /path/to/file.csv [--dry-run]
"""

import csv
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

csv.field_size_limit(sys.maxsize)

# ──────────────────── CAMPI DA ESCLUDERE ──────────────────────────
# search_vector: generato automaticamente da PostgreSQL (TSVector)
SKIP_COLUMNS = {"search_vector"}

# ──────────────────── MAPPING TIPI PER COLONNA ────────────────────
# Colonne Date (db.Date)
DATE_COLUMNS = {
    "data_di_nascita",
    "data_inizio_abbonamento",
    "data_call_iniziale_nutrizionista",
    "data_call_iniziale_psicologia",
    "data_call_iniziale_coach",
    "data_rinnovo",
    "data_test_alim",
    "allenamento_dal",
    "nuovo_allenamento_il",
    "dieta_dal",
    "nuova_dieta_dal",
    "onboarding_date",
}

# Colonne DateTime (db.DateTime)
DATETIME_COLUMNS = {
    "created_at",
    "updated_at",
    "stato_psicologia_data",
    "stato_nutrizione_data",
    "stato_coach_data",
    "stato_cliente_data",
    "freeze_date",
    "ghl_last_sync",
    "payment_verified_at",
    "service_activated_at",
    "service_assignment_date",
    "ghl_last_modified",
    "ultima_recensione_trustpilot_data",
    "goals_evaluation_date",
}

# Colonne Boolean (db.Boolean)
BOOLEAN_COLUMNS = {
    "bonus",
    "alert",
    "call_iniziale_nutrizionista",
    "call_iniziale_coach",
    "call_iniziale_psicologa",
    "no_social",
    "social_oscurato",
    "video_feedback",
    "proposta_live_training",
    "live_training_proposte",
    "live_training_bonus_prenotata",
    "video_feedback_richiesto",
    "video_feedback_svolto",
    "video_feedback_condiviso",
    "trasformazione_fisica",
    "trasformazione_fisica_condivisa",
    "exit_call_richiesta",
    "exit_call_svolta",
    "exit_call_condivisa",
    "consenso_social_richiesto",
    "consenso_social_accettato",
    "recensione_richiesta",
    "recensione_accettata",
    "recensione_risposta",
    "is_frozen",
    "has_goals_left",
    "nessuna_patologia",
    "patologia_ibs",
    "patologia_reflusso",
    "patologia_gastrite",
    "patologia_dca",
    "patologia_insulino_resistenza",
    "patologia_diabete",
    "patologia_dislipidemie",
    "patologia_steatosi_epatica",
    "patologia_ipertensione",
    "patologia_pcos",
    "patologia_endometriosi",
    "patologia_obesita_sindrome",
    "patologia_osteoporosi",
    "patologia_diverticolite",
    "patologia_crohn",
    "patologia_stitichezza",
    "patologia_tiroidee",
    "nessuna_patologia_psico",
    "patologia_psico_dca",
    "patologia_psico_obesita_psicoemotiva",
    "patologia_psico_ansia_umore_cibo",
    "patologia_psico_comportamenti_disfunzionali",
    "patologia_psico_immagine_corporea",
    "patologia_psico_psicosomatiche",
    "patologia_psico_relazionali_altro",
}

# Colonne Integer (db.Integer / db.BigInteger)
INTEGER_COLUMNS = {
    "cliente_id",
    "durata_programma_giorni",
    "nutrizionista_id",
    "coach_id",
    "psicologa_id",
    "consulente_alimentare_id",
    "health_manager_id",
    "created_by",
    "frozen_by_id",
    "unfrozen_by_id",
    "sedute_psicologia_comprate",
    "sedute_psicologia_svolte",
    "recensione_stelle",
    "ghl_modification_count",
    "payment_verified_by",
    "evaluated_by_user_id",
    "recensioni_lifetime_count",
}

# Colonne Numeric/Decimal (db.Numeric)
DECIMAL_COLUMNS = {
    "rate_cliente_sales",
    "deposito_iniziale",
}

# Colonne Enum: nome_colonna → set di valori validi
ENUM_COLUMNS = {
    "stato_cliente": {"attivo", "ghost", "pausa", "stop"},
    "stato_cliente_chat": {"attivo", "ghost", "pausa", "stop"},
    "stato_cliente_chat_nutrizione": {"attivo", "ghost", "pausa", "stop"},
    "stato_cliente_chat_coaching": {"attivo", "ghost", "pausa", "stop"},
    "stato_cliente_chat_psicologia": {"attivo", "ghost", "pausa", "stop"},
    "stato_psicologia": {"attivo", "ghost", "pausa", "stop"},
    "stato_nutrizione": {"attivo", "ghost", "pausa", "stop"},
    "stato_coach": {"attivo", "ghost", "pausa", "stop"},
    "di_team": {"interno", "sales_team", "setter_team", "sito", "va_team"},
    "modalita_pagamento": {"bonifico", "klarna", "stripe", "paypal", "carta", "contanti"},
    "tipologia_cliente": {"a", "b", "c", "stop", "recupero", "pausa_gt_30"},
    "check_day": {"lun", "mar", "mer", "gio", "ven", "sab", "dom",
                  "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"},
    "check_saltati": {"1", "2", "3", "3_plus"},
    "reach_out": {"lun", "mar", "mer", "gio", "ven", "sab", "dom",
                  "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"},
    "reach_out_nutrizione": {"lun", "mar", "mer", "gio", "ven", "sab", "dom",
                             "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"},
    "reach_out_coaching": {"lun", "mar", "mer", "gio", "ven", "sab", "dom",
                           "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"},
    "reach_out_psicologia": {"lun", "mar", "mer", "gio", "ven", "sab", "dom",
                             "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"},
    "luogo_di_allenamento": {"casa", "palestra", "ibrido"},
    "figura_di_riferimento": {"coach", "nutrizionista", "psicologa"},
    "trasformazione": {"no", "si"},
}

# Tutte le altre colonne sono Text/String (nessuna conversione necessaria)


# ──────────────────── FUNZIONI DI CONVERSIONE ─────────────────────

def parse_value(col: str, raw: str):
    """Converte il valore grezzo CSV nel tipo Python corretto per il modello."""
    # Vuoto → None
    if raw is None or raw.strip() == "":
        return None

    val = raw.strip()

    # Skip
    if col in SKIP_COLUMNS:
        return "__SKIP__"

    # Boolean
    if col in BOOLEAN_COLUMNS:
        if val.lower() in ("true", "1", "yes", "t", "si", "sì"):
            return True
        if val.lower() in ("false", "0", "no", "f"):
            return False
        return None

    # Integer
    if col in INTEGER_COLUMNS:
        try:
            return int(float(val))  # float() gestisce "180.0" → 180
        except (ValueError, OverflowError):
            return None

    # Decimal
    if col in DECIMAL_COLUMNS:
        try:
            return Decimal(val)
        except InvalidOperation:
            return None

    # Date
    if col in DATE_COLUMNS:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    # DateTime
    if col in DATETIME_COLUMNS:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        return None

    # Enum
    if col in ENUM_COLUMNS:
        if val in ENUM_COLUMNS[col]:
            return val
        # Prova lowercase
        if val.lower() in ENUM_COLUMNS[col]:
            return val.lower()
        return None  # Valore non valido per l'enum → skip

    # Tutto il resto → stringa (Text, String)
    return val


def parse_row(headers: list[str], row_dict: dict[str, str]) -> dict:
    """Parsa un'intera riga CSV e ritorna un dict pronto per il modello Cliente."""
    parsed = {}
    for col in headers:
        if col in SKIP_COLUMNS:
            continue
        raw = row_dict.get(col, "")
        value = parse_value(col, raw)
        if value != "__SKIP__":
            parsed[col] = value
    return parsed


# ──────────────────── FUNZIONE PRINCIPALE ─────────────────────────

def import_clienti(csv_path: str, dry_run: bool = False):
    """Importa clienti dal CSV nel database."""
    from corposostenibile import create_app
    from corposostenibile.models import Cliente, User, db

    app = create_app()
    with app.app_context():
        # 1. Leggi CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)

        total = len(rows)
        print(f"\n{'='*60}")
        print(f"  IMPORT CLIENTI DAL CSV")
        print(f"  File: {csv_path}")
        print(f"  Righe: {total}")
        print(f"  Modalità: {'DRY-RUN (nessuna scrittura)' if dry_run else 'LIVE'}")
        print(f"{'='*60}\n")

        # 2. Validazione FK: controlla che i professionisti esistano
        fk_fields = ["nutrizionista_id", "coach_id", "psicologa_id",
                      "consulente_alimentare_id", "health_manager_id",
                      "created_by", "frozen_by_id", "unfrozen_by_id",
                      "evaluated_by_user_id", "payment_verified_by"]

        all_user_ids = set()
        for row in rows:
            for fk in fk_fields:
                val = row.get(fk, "").strip()
                if val:
                    try:
                        all_user_ids.add(int(float(val)))
                    except (ValueError, OverflowError):
                        pass

        existing_user_ids = set()
        if all_user_ids:
            existing_users = User.query.filter(User.id.in_(all_user_ids)).all()
            existing_user_ids = {u.id for u in existing_users}

        missing_user_ids = all_user_ids - existing_user_ids
        if missing_user_ids:
            print(f"⚠  User IDs referenziati ma NON presenti nel DB: {sorted(missing_user_ids)}")
            print(f"   I campi FK con questi ID verranno impostati a NULL.\n")

        # 3. Controlla duplicati (cliente_id già esistenti)
        csv_ids = []
        for row in rows:
            cid = row.get("cliente_id", "").strip()
            if cid:
                try:
                    csv_ids.append(int(float(cid)))
                except (ValueError, OverflowError):
                    pass

        existing_clienti = set()
        if csv_ids:
            existing = Cliente.query.filter(Cliente.cliente_id.in_(csv_ids)).all()
            existing_clienti = {c.cliente_id for c in existing}

        if existing_clienti:
            print(f"⚠  {len(existing_clienti)} clienti già presenti nel DB (verranno AGGIORNATI):")
            print(f"   IDs: {sorted(existing_clienti)[:20]}{'...' if len(existing_clienti) > 20 else ''}\n")

        new_count = len(csv_ids) - len(existing_clienti)
        update_count = len(existing_clienti)
        print(f"  → {new_count} nuovi clienti da INSERIRE")
        print(f"  → {update_count} clienti da AGGIORNARE\n")

        if dry_run:
            # Validazione parsing di tutte le righe
            errors = []
            for i, row in enumerate(rows):
                try:
                    parsed = parse_row(headers, row)
                    nome = parsed.get("nome_cognome", "(senza nome)")
                    cid = parsed.get("cliente_id", "?")

                    # Controlla FK non valide
                    for fk in fk_fields:
                        val = parsed.get(fk)
                        if val is not None and val not in existing_user_ids:
                            errors.append(f"  Riga {i+1} ({nome}, ID {cid}): {fk}={val} non esiste in users")
                except Exception as e:
                    errors.append(f"  Riga {i+1}: errore parsing: {e}")

            if errors:
                print(f"⚠  Problemi rilevati ({len(errors)}):")
                for err in errors[:30]:
                    print(err)
                if len(errors) > 30:
                    print(f"  ... e altri {len(errors) - 30}")
            else:
                print("✓  Tutte le righe parsano correttamente.")

            print(f"\n{'='*60}")
            print(f"  DRY-RUN COMPLETATO — nessuna modifica al DB")
            print(f"{'='*60}\n")
            return

        # 4. Import effettivo
        created = 0
        updated = 0
        skipped = 0
        errors = []

        for i, row in enumerate(rows):
            try:
                parsed = parse_row(headers, row)
                cid = parsed.get("cliente_id")

                if cid is None:
                    errors.append(f"  Riga {i+1}: cliente_id mancante, skip")
                    skipped += 1
                    continue

                # Annulla FK con user_id inesistenti
                for fk in fk_fields:
                    val = parsed.get(fk)
                    if val is not None and val not in existing_user_ids:
                        parsed[fk] = None

                # Upsert basato su cliente_id
                cliente = Cliente.query.get(cid)
                if cliente:
                    # Aggiorna campi esistenti
                    for k, v in parsed.items():
                        if k == "cliente_id":
                            continue
                        if hasattr(cliente, k) and not k.startswith("_"):
                            setattr(cliente, k, v)
                    updated += 1
                else:
                    # Nuovo cliente
                    clean = {k: v for k, v in parsed.items()
                             if hasattr(Cliente, k) and not k.startswith("_")}
                    cliente = Cliente(**clean)
                    db.session.add(cliente)
                    created += 1

                # Flush ogni 50 per evitare problemi di memoria
                if (i + 1) % 50 == 0:
                    db.session.flush()
                    print(f"  ... processati {i+1}/{total}")

            except Exception as e:
                nome = row.get("nome_cognome", "?")
                errors.append(f"  Riga {i+1} ({nome}): {e}")
                skipped += 1

        # 5. Commit
        try:
            db.session.commit()
            print(f"\n{'='*60}")
            print(f"  IMPORT COMPLETATO CON SUCCESSO!")
            print(f"  ✓ Creati:     {created}")
            print(f"  ✓ Aggiornati: {updated}")
            if skipped:
                print(f"  ⚠ Saltati:    {skipped}")
            print(f"{'='*60}\n")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗  ERRORE COMMIT: {e}")
            print("   Rollback eseguito, nessuna modifica salvata.\n")
            raise

        if errors:
            print(f"Errori ({len(errors)}):")
            for err in errors:
                print(err)


# ──────────────────── ENTRY POINT ─────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import clienti dal CSV")
    parser.add_argument("csv_file", help="Path al file CSV")
    parser.add_argument("--dry-run", action="store_true", help="Valida senza scrivere nel DB")
    args = parser.parse_args()

    if not Path(args.csv_file).exists():
        print(f"Errore: file '{args.csv_file}' non trovato.")
        sys.exit(1)

    import_clienti(args.csv_file, dry_run=args.dry_run)
