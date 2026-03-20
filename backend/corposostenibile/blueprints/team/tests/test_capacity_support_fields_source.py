from __future__ import annotations

from pathlib import Path


TEAM_API_FILE = Path(__file__).resolve().parents[1] / "api.py"


def _extract_function_source(source: str, fn_name: str) -> str:
    marker = f"def {fn_name}("
    start = source.find(marker)
    assert start != -1, f"Funzione non trovata: {fn_name}"

    end = source.find("\ndef ", start + 1)
    if end == -1:
        end = len(source)
    return source[start:end]


def test_capacity_breakdown_uses_support_fields_and_secondary_bucket() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")
    fn_source = _extract_function_source(source, "_get_assigned_clients_by_type")

    assert "Cliente.tipologia_supporto_nutrizione" in fn_source
    assert "Cliente.tipologia_supporto_coach" in fn_source
    assert "CAPACITY_SUPPORT_TYPES" in fn_source


def test_capacity_weight_endpoints_use_role_specific_weights() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")

    assert "CapacityRoleTypeWeight" in source
    assert "DEFAULT_CAPACITY_WEIGHTS" in source
    assert "_get_capacity_weights_by_role()" in source
