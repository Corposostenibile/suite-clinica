"""Utilities per parsare il pacchetto e derivare le tipologie di supporto."""

from __future__ import annotations

import re
from typing import Any


ROLE_MAP = {
    "N": "nutrizione",
    "C": "coach",
    "P": "psicologia",
}

PRIMARY_TYPES = {"a", "b", "c"}
SECONDARY_TYPE = "secondario"


def _ordered_role_letters(package_name: str | None) -> list[str]:
    if not package_name:
        return []

    first_segment = str(package_name).split("-", 1)[0].upper()
    ordered: list[str] = []
    for char in first_segment:
        if char in ROLE_MAP and char not in ordered:
            ordered.append(char)
    return ordered


def _extract_duration_days(package_name: str | None) -> int:
    if not package_name:
        return 0

    for segment in str(package_name).split("-")[1:]:
        match = re.search(r"(\d+)", segment)
        if match:
            return int(match.group(1))
    return 0


def _extract_client_type(package_name: str | None) -> str | None:
    if not package_name:
        return None

    parts = [part.strip() for part in str(package_name).split("-") if part.strip()]
    for part in reversed(parts[1:]):
        candidate = re.sub(r"[^A-Z]", "", part.upper())
        if candidate in {"A", "B", "C"}:
            return candidate.lower()

    trailing = re.search(r"([ABC])\s*$", str(package_name).upper())
    if trailing:
        return trailing.group(1).lower()
    return None


def parse_package_support(package_name: str | None) -> dict[str, Any]:
    """
    Parsa il nome pacchetto preservando l'ordine dei ruoli e la tipologia finale.

    Esempi supportati:
    - ``NC-180-C`` -> nutrizione: c, coach: secondario
    - ``CN-180-A`` -> coach: a, nutrizione: secondario
    - ``N/C+P-90gg-B`` -> nutrizione: b, coach: secondario, psicologia presente
    """
    role_letters = _ordered_role_letters(package_name)
    ordered_roles = [ROLE_MAP[char] for char in role_letters]
    client_type = _extract_client_type(package_name)
    duration_days = _extract_duration_days(package_name)

    support = {
        "nutrizione": None,
        "coach": None,
    }

    ordered_support_roles = [role for role in ordered_roles if role in support]
    if ordered_support_roles:
        primary_role = ordered_support_roles[0]
        support[primary_role] = client_type
        for secondary_role in ordered_support_roles[1:]:
            support[secondary_role] = SECONDARY_TYPE

    return {
        "raw": package_name or "",
        "ordered_roles": ordered_roles,
        "roles": {
            "nutrition": "nutrizione" in ordered_roles,
            "coach": "coach" in ordered_roles,
            "psychology": "psicologia" in ordered_roles,
        },
        "duration_days": duration_days,
        "client_type": client_type,
        "support_types": support,
        "code": "".join(role_letters),
    }
