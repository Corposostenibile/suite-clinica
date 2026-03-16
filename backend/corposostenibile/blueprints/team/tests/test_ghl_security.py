from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")

from corposostenibile import create_app
from corposostenibile.blueprints.ghl_integration.security import (
    _is_signature_verification_optional,
)


def test_signature_verification_is_optional_in_testing_app() -> None:
    app = create_app("testing")
    with app.app_context():
        assert _is_signature_verification_optional() is True


def test_signature_verification_is_optional_when_flask_env_is_development(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "development")
    app = create_app("development")
    app.debug = False
    app.testing = False

    with app.app_context():
        assert _is_signature_verification_optional() is True
