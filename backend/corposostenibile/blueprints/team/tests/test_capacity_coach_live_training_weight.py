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


def test_capacity_metrics_adds_live_training_weight_for_coach() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")
    fn_source = _extract_function_source(source, "_calculate_capacity_metrics")

    assert 'if role_type == "coach"' in fn_source
    assert "weighted_load += float(coach_live_training_load or 0.0)" in fn_source


def test_coach_live_training_load_uses_linear_weight_0_3() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")
    fn_source = _extract_function_source(source, "_get_coach_live_training_load_map")

    assert "live_trainings_svolte" in fn_source
    assert "* 0.3" in fn_source


def test_coach_live_training_load_deduplicates_same_client_assignments() -> None:
    source = TEAM_API_FILE.read_text(encoding="utf-8")
    fn_source = _extract_function_source(source, "_get_coach_live_training_load_map")

    assert "func.max(coach_sq.c.live_trainings_svolte)" in fn_source
    assert "group_by(" in fn_source
    assert "coach_sq.c.user_id" in fn_source
    assert "coach_sq.c.cliente_id" in fn_source
