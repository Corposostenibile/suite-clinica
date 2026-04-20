from __future__ import annotations

import pytest

from corposostenibile.models import User


def _get_admin_user_id() -> int:
    admin = User.query.filter_by(is_admin=True).order_by(User.id.asc()).first()
    if not admin:
        pytest.skip("No admin user available for GHL assignments alias test")
    return int(admin.id)


def test_sales_ghl_assignments_alias_matches_ghl_integration_endpoint(app):
    with app.app_context():
        admin_id = _get_admin_user_id()
        client = app.test_client()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_id)
            sess["_fresh"] = True

        alias_response = client.get("/api/ghl-assignments", query_string={"status": "all"})
        legacy_response = client.get("/ghl/api/assignments", query_string={"status": "all"})

        assert alias_response.status_code == 200
        assert legacy_response.status_code == 200
        assert alias_response.get_json() == legacy_response.get_json()
