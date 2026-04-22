"""
Utility per validare/normalizzare i payload dei check JSON-driven.

Questa utility e' usata dai check nuovi (weekly-light e monthly)
per avere regole coerenti e centralizzate.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def validate_json_check_payload(
    payload: Dict[str, Any],
    questions: List[Dict[str, Any]],
    *,
    required_types: Iterable[str] = ("scale", "select", "number"),
) -> Tuple[Dict[str, Any], str | None]:
    """
    Valida e normalizza un payload rispetto a una lista domande.

    Returns:
        (normalized_payload, error_message)
        - normalized_payload: valori coerenti con i tipi definiti
        - error_message: None se ok, testo errore se invalid
    """
    required_types_set = set(required_types)
    normalized: Dict[str, Any] = {}
    missing_required: List[str] = []

    for question in questions:
        key = question.get("key")
        qtype = question.get("type")
        if not key or not qtype:
            continue

        is_required = bool(question.get("required", True))
        raw_value = payload.get(key)
        has_value = key in payload and raw_value is not None

        if is_required and qtype in required_types_set and not has_value:
            missing_required.append(key)
            continue

        if not has_value:
            continue

        if qtype == "scale":
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                return {}, f"Valore non valido per {key}"

            qmin = question.get("min")
            qmax = question.get("max")
            if qmin is not None and value < int(qmin):
                return {}, f"Valore fuori range per {key}"
            if qmax is not None and value > int(qmax):
                return {}, f"Valore fuori range per {key}"
            normalized[key] = value
            continue

        if qtype == "number":
            if raw_value == "":
                if is_required and qtype in required_types_set:
                    missing_required.append(key)
                continue
            try:
                normalized[key] = float(raw_value)
            except (TypeError, ValueError):
                return {}, f"Valore numerico non valido per {key}"
            continue

        if qtype == "select":
            value = str(raw_value).strip()
            options = question.get("options") or []
            if options and value not in options:
                return {}, f"Opzione non valida per {key}"
            if not value and is_required and qtype in required_types_set:
                missing_required.append(key)
                continue
            normalized[key] = value
            continue

        if qtype == "text":
            value = str(raw_value).strip()
            if value:
                normalized[key] = value
            elif is_required and qtype in required_types_set:
                missing_required.append(key)
            continue

        # Fallback: preserva tipi non gestiti esplicitamente
        normalized[key] = raw_value

    if missing_required:
        missing = ", ".join(sorted(missing_required))
        return {}, f"Campi mancanti: {missing}"

    return normalized, None
