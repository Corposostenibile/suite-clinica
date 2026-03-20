from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")

from corposostenibile import create_app
from corposostenibile.blueprints.customers.routes import (
    _extract_trustpilot_webhook_fields,
    _get_trustpilot_missing_config,
    _is_trustpilot_webhook_configured,
)


def test_extract_trustpilot_webhook_fields_from_nested_payload() -> None:
    payload = {
        "eventType": "review.published",
        "invitation": {
            "id": "inv-123",
            "referenceId": "ref-456",
        },
        "review": {
            "id": "rev-789",
            "stars": 5,
            "title": "Ottimo",
            "text": "Esperienza eccellente",
            "publishedAt": "2026-03-20T10:10:00Z",
        },
    }

    fields = _extract_trustpilot_webhook_fields(payload)

    assert fields["event_type"] == "review.published"
    assert fields["invitation_id"] == "inv-123"
    assert fields["reference_id"] == "ref-456"
    assert fields["review_id"] == "rev-789"
    assert fields["stars"] == 5
    assert fields["title"] == "Ottimo"
    assert fields["text"] == "Esperienza eccellente"
    assert fields["published_at"] is not None
    assert fields["is_published_event"] is True
    assert fields["is_deleted_event"] is False


def test_extract_trustpilot_webhook_fields_marks_deleted_event() -> None:
    payload = {
        "type": "review.deleted",
        "reference_id": "ref-777",
        "deleted_at": "2026-03-20T11:22:00Z",
    }

    fields = _extract_trustpilot_webhook_fields(payload)

    assert fields["reference_id"] == "ref-777"
    assert fields["deleted_at"] is not None
    assert fields["is_deleted_event"] is True


def test_trustpilot_config_helpers_detect_missing_and_webhook_creds() -> None:
    app = create_app("testing")
    app.config.update(
        TRUSTPILOT_API_KEY="",
        TRUSTPILOT_API_SECRET="secret",
        TRUSTPILOT_BUSINESS_UNIT_ID="",
        TRUSTPILOT_WEBHOOK_USERNAME="",
        TRUSTPILOT_WEBHOOK_PASSWORD="",
    )

    with app.app_context():
        missing = _get_trustpilot_missing_config()
        assert "TRUSTPILOT_API_KEY" in missing
        assert "TRUSTPILOT_BUSINESS_UNIT_ID" in missing
        assert _is_trustpilot_webhook_configured() is False

    app.config.update(
        TRUSTPILOT_WEBHOOK_USERNAME="tp-user",
        TRUSTPILOT_WEBHOOK_PASSWORD="tp-pass",
    )
    with app.app_context():
        assert _is_trustpilot_webhook_configured() is True
