from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")

from corposostenibile.blueprints.team.api import _calculate_capacity_metrics


def test_nutrizione_capacity_metrics_follow_call_weighting() -> None:
    metrics = _calculate_capacity_metrics(
        role_type="nutrizionista",
        assigned_clients=4,
        contractual_capacity=5,
        type_counts={"a": 1, "b": 1, "c": 1, "secondario": 1},
        weights_by_role={
            "nutrizione": {"a": 2.0, "b": 1.5, "c": 1.0, "secondario": 0.5},
            "coach": {"a": 9.0, "b": 9.0, "c": 9.0, "secondario": 9.0},
        },
    )

    assert metrics["clienti_tipo_a"] == 1
    assert metrics["clienti_tipo_b"] == 1
    assert metrics["clienti_tipo_c"] == 1
    assert metrics["clienti_tipo_secondario"] == 1
    assert metrics["capienza_ponderata"] == 5.0
    assert metrics["percentuale_capienza"] == 100.0
    assert metrics["is_over_capacity"] is False


def test_coach_capacity_metrics_use_role_specific_weights() -> None:
    metrics = _calculate_capacity_metrics(
        role_type="coach",
        assigned_clients=3,
        contractual_capacity=4,
        type_counts={"a": 1, "c": 1, "secondario": 1},
        weights_by_role={
            "nutrizione": {"a": 2.0, "b": 1.5, "c": 1.0, "secondario": 0.5},
            "coach": {"a": 3.0, "b": 2.0, "c": 1.0, "secondario": 0.25},
        },
    )

    assert metrics["capienza_ponderata"] == 4.25
    assert metrics["percentuale_capienza"] == 106.25
    assert metrics["is_over_capacity"] is True


def test_psicologa_capacity_is_always_plain_client_count() -> None:
    metrics = _calculate_capacity_metrics(
        role_type="psicologa",
        assigned_clients=3,
        contractual_capacity=5,
        type_counts={"a": 10, "b": 10, "c": 10, "secondario": 10},
        weights_by_role={},
    )

    assert metrics["capienza_ponderata"] == 3.0
    assert metrics["percentuale_capienza"] == 60.0
    assert metrics["is_over_capacity"] is False


def test_health_manager_capacity_remains_count_based() -> None:
    metrics = _calculate_capacity_metrics(
        role_type="health_manager",
        assigned_clients=7,
        contractual_capacity=6,
        type_counts={"a": 2, "b": 1, "c": 3, "secondario": 1},
        weights_by_role={
            "nutrizione": {"a": 2.0, "b": 1.5, "c": 1.0, "secondario": 0.5},
            "coach": {"a": 2.0, "b": 1.5, "c": 1.0, "secondario": 0.5},
        },
    )

    assert metrics["capienza_ponderata"] == 7.0
    assert metrics["percentuale_capienza"] == 116.67
    assert metrics["is_over_capacity"] is True
