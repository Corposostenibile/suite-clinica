from __future__ import annotations

from corposostenibile.package_support import parse_package_support


def test_parse_package_support_nc_marks_nutrition_primary_and_coach_secondary() -> None:
    parsed = parse_package_support("NC-180-C")

    assert parsed["client_type"] == "c"
    assert parsed["duration_days"] == 180
    assert parsed["support_types"]["nutrizione"] == "c"
    assert parsed["support_types"]["coach"] == "secondario"


def test_parse_package_support_cn_marks_coach_primary_and_nutrition_secondary() -> None:
    parsed = parse_package_support("CN-180-A")

    assert parsed["client_type"] == "a"
    assert parsed["support_types"]["coach"] == "a"
    assert parsed["support_types"]["nutrizione"] == "secondario"


def test_parse_package_support_keeps_psychology_without_support_weight() -> None:
    parsed = parse_package_support("N/C+P-90gg-B")

    assert parsed["roles"]["psychology"] is True
    assert parsed["support_types"]["nutrizione"] == "b"
    assert parsed["support_types"]["coach"] == "secondario"
