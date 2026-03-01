"""Utilities per determinare i professionisti richiesti da un pacchetto."""

from __future__ import annotations

from typing import Dict


def normalize_package_code(package_name: str | None) -> str:
    """Normalizza un codice pacchetto in formato lettere (es: NCP, NC, P)."""
    if not package_name:
        return ""

    cleaned = "".join(ch for ch in str(package_name).upper() if ch.isalpha())
    letters_only = "".join(ch for ch in cleaned if ch in {"N", "C", "P"})
    unique_ordered = "".join(ch for ch in "NCP" if ch in letters_only)

    # Considera "codice compatto" solo se contiene esclusivamente N/C/P
    if unique_ordered and len(cleaned) <= 3 and set(cleaned).issubset({"N", "C", "P"}):
        return unique_ordered
    return ""


def get_package_requirements(package_name: str | None) -> Dict[str, bool]:
    """
    Determina i professionisti richiesti dal pacchetto.

    Supporta:
    - Nuovo formato codice: NCP, NC, NP, CP, N, C, P
    - Fallback legacy su nome pacchetto descrittivo
    """
    code = normalize_package_code(package_name)
    if code:
        return {
            "nutrizionista": "N" in code,
            "coach": "C" in code,
            "psicologa": "P" in code,
        }

    if not package_name:
        return {"nutrizionista": True, "coach": True, "psicologa": True}

    package_lower = str(package_name).lower()
    return {
        "nutrizionista": True,
        "coach": True,
        "psicologa": (
            "premium" in package_lower
            or "vip" in package_lower
            or "completo" in package_lower
        ),
    }
