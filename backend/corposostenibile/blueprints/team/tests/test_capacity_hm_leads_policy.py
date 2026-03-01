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


def test_hm_capacity_counts_pending_assignment_from_cliente() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")
    fn_source = _extract_function_source(source, "_get_assigned_clients_count_map_active_by_role")

    assert "Cliente.service_status == 'pending_assignment'" in fn_source
    assert "Cliente.health_manager_id" in fn_source


def test_hm_capacity_does_not_depend_on_ghl_email_matching() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")
    fn_source = _extract_function_source(source, "_get_assigned_clients_count_map_active_by_role")

    assert "GHLOpportunityData.health_manager_email" not in fn_source
