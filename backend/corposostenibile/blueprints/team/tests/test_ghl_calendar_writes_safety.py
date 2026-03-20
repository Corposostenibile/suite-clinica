from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")

from corposostenibile import create_app
from corposostenibile.blueprints.ghl_integration.routes import _mock_calendar_writes_enabled


def test_calendar_writes_are_mocked_in_testing_environment() -> None:
    app = create_app("testing")
    with app.app_context():
        assert _mock_calendar_writes_enabled() is True


def test_calendar_writes_can_be_forced_in_testing_with_flag() -> None:
    app = create_app("testing")
    app.config["GHL_CALENDAR_ALLOW_WRITES"] = True
    with app.app_context():
        assert _mock_calendar_writes_enabled() is False
