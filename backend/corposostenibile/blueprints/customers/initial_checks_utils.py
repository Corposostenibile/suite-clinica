from __future__ import annotations

import re
from typing import Any


def normalize_initial_check_responses(raw: Any) -> dict[str, Any]:
    """
    Normalizza le risposte dei check iniziali in formato dict.

    Alcuni record legacy salvano check*_responses come stringa multilinea:
    "chiave: valore\\nchiave2: valore2\\n..."
    """
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}

    parsed: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        match = re.match(r"^([a-zA-Z0-9_]+):\s*(.*)$", line)
        if match:
            current_key = match.group(1)
            parsed[current_key] = match.group(2) or ""
        elif current_key:
            parsed[current_key] = f"{parsed[current_key]}\n{line}" if parsed[current_key] else line
    return parsed
