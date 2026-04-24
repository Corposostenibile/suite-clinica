"""Pulisce i fallback di errore dalla cache `ai_analysis` (memory-safe).

Contesto: quando Gemini AI fallisce (timeout / rate limit / JSON malformato)
`AIMatchingService.extract_lead_criteria` ritorna un placeholder
`{"summary": "Errore analisi", ...}` invece di sollevare eccezione.
L'endpoint `/team/assignments/analyze-lead` salva quel placeholder in DB;
al prossimo open del lead il backend serve il cached senza richiamare l'AI
-> l'utente vede "errore analisi" a vita. Questo script ripulisce la cache.

Comportamento:
- **Filter SERVER-SIDE**: carica SOLO le righe che contengono una stringa di
  errore nel JSON (ai_analysis::text ILIKE) - niente caricamento a memoria
  di tutte le righe (previene OOMKill sul pod backend).
- Row-by-row: commit dopo ogni record + expunge_all -> memoria costante O(1).
- Per ogni record pulisce SOLO le chiavi role con summary di errore (e il
  blocco legacy top-level se in errore), preservando i role validi.

Usage:
    docker compose -f docker-compose.dev.yml exec backend \
      python /app/scripts/purge_ai_analysis_errors.py --dry-run
    kubectl exec deployment/suite-clinica-backend -c backend -- \
      python /app/scripts/purge_ai_analysis_errors.py
"""
import argparse

from sqlalchemy import or_

from corposostenibile import create_app
from corposostenibile.extensions import db

ERROR_SUMMARIES = {
    "Errore analisi",
    "Errore sistemico",
    "Nessuna risposta dall'AI",
}
LEGACY_KEYS = {"summary", "criteria", "suggested_focus"}


def _clean_analysis(payload):
    """Ritorna (new_payload_or_None, changed: bool). Vedi docstring script."""
    if not isinstance(payload, dict):
        return payload, False

    cleaned = {}
    changed = False

    top_summary = payload.get("summary")
    if isinstance(top_summary, str) and top_summary in ERROR_SUMMARIES:
        changed = True
    else:
        for k in LEGACY_KEYS:
            if k in payload:
                cleaned[k] = payload[k]

    for role_key, role_val in payload.items():
        if role_key in LEGACY_KEYS:
            continue
        if isinstance(role_val, dict) and role_val.get("summary") in ERROR_SUMMARIES:
            changed = True
            continue
        cleaned[role_key] = role_val

    if not cleaned:
        return None, changed or bool(payload)
    return cleaned, changed


def _purge_model(model, label, *, touched_at_field=None, dry_run=True):
    """Filter server-side -> carica solo righe dirty, processa row-by-row."""
    # SQL-side ILIKE: scarta a livello DB le righe senza errore nel JSON.
    conditions = [
        db.cast(model.ai_analysis, db.Text).ilike(f"%{needle}%")
        for needle in ERROR_SUMMARIES
    ]
    stream = (
        db.session.query(model.id, model.ai_analysis)
        .filter(model.ai_analysis.isnot(None))
        .filter(or_(*conditions))
        .yield_per(50)
    )

    touched = 0
    wiped = 0

    for row_id, ai_analysis in stream:
        new_val, changed = _clean_analysis(ai_analysis)
        if not changed:
            continue
        touched += 1
        if new_val is None:
            wiped += 1
        if not dry_run:
            update_values = {"ai_analysis": new_val}
            if touched_at_field and new_val is None and hasattr(model, touched_at_field):
                update_values[touched_at_field] = None
            # UPDATE diretto senza caricare l'oggetto ORM (zero memoria)
            db.session.query(model).filter(model.id == row_id).update(update_values, synchronize_session=False)
            db.session.commit()
            db.session.expire_all()

    print(f"  {label:28s} toccati={touched:4d}  azzerati={wiped:4d}")
    return touched, wiped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Simula senza scrivere")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from corposostenibile.models import SalesLead  # noqa: WPS433
        try:
            from corposostenibile.models import GHLOpportunityData  # noqa: WPS433
        except ImportError:
            GHLOpportunityData = None
        try:
            from corposostenibile.models import ServiceClienteAssignment  # noqa: WPS433
        except ImportError:
            ServiceClienteAssignment = None

        mode = "DRY-RUN" if args.dry_run else "APPLY"
        print(f"[purge_ai_analysis_errors] mode={mode}")

        tot_touched = 0
        tot_wiped = 0

        t, w = _purge_model(SalesLead, "SalesLead", touched_at_field="ai_analyzed_at", dry_run=args.dry_run)
        tot_touched += t
        tot_wiped += w

        if GHLOpportunityData is not None:
            t, w = _purge_model(GHLOpportunityData, "GHLOpportunityData", touched_at_field="ai_analyzed_at", dry_run=args.dry_run)
            tot_touched += t
            tot_wiped += w

        if ServiceClienteAssignment is not None:
            t, w = _purge_model(ServiceClienteAssignment, "ServiceClienteAssignment", touched_at_field="ai_suggested_at", dry_run=args.dry_run)
            tot_touched += t
            tot_wiped += w

        print(f"\nTOTALE  toccati={tot_touched}  azzerati={tot_wiped}  mode={mode}")


if __name__ == "__main__":
    main()
