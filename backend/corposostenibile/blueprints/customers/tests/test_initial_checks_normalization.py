from __future__ import annotations

import pytest

from corposostenibile.blueprints.customers.initial_checks_utils import (
    normalize_initial_check_responses,
)


def test_normalize_initial_check_responses_keeps_dict_unchanged() -> None:
    payload = {"email": "test@example.com", "first_name": "Mario"}
    assert normalize_initial_check_responses(payload) == payload


def test_normalize_initial_check_responses_parses_legacy_string() -> None:
    raw = (
        "email: info@example.com\n"
        "first_name: Mario\n"
        "giornata_tipo_recall: Colazione:\n"
        "ore 6\n"
        "yogurt\n"
        "privacy_accepted: Accetto"
    )

    normalized = normalize_initial_check_responses(raw)

    assert normalized["email"] == "info@example.com"
    assert normalized["first_name"] == "Mario"
    assert normalized["privacy_accepted"] == "Accetto"
    assert normalized["giornata_tipo_recall"] == "Colazione:\nore 6\nyogurt"


@pytest.mark.parametrize("raw", [None, 42, 3.14, ["a", "b"]])
def test_normalize_initial_check_responses_returns_empty_dict_for_non_supported_types(raw) -> None:
    assert normalize_initial_check_responses(raw) == {}
