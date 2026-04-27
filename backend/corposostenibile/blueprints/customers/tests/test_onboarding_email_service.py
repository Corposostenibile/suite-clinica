from __future__ import annotations

from types import SimpleNamespace

from flask import Flask

from corposostenibile.blueprints.customers import services
from corposostenibile.extensions import mail


class _FakeSession:
    def __init__(self, cliente):
        self._cliente = cliente
        self.committed = False
        self.rolled_back = False

    def get(self, model, pk):
        return self._cliente if pk == self._cliente.cliente_id else None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_send_onboarding_email_sends_once_and_sets_timestamp(monkeypatch) -> None:
    app = Flask(__name__)
    app.config["MAIL_SERVER"] = "smtp.test.local"
    app.config["MAIL_DEFAULT_SENDER"] = "noreply@test.local"

    cliente = SimpleNamespace(
        cliente_id=101,
        nome_cognome="Mario Rossi",
        mail="mario@example.com",
        onboarding_email_sent_at=None,
        health_manager_user=SimpleNamespace(full_name="HM Test"),
    )
    fake_session = _FakeSession(cliente)
    sent = {"count": 0, "html": None, "subject": None, "to": None}

    monkeypatch.setattr(services.db, "session", fake_session)
    monkeypatch.setattr(
        services,
        "_build_check_links_for_onboarding",
        lambda _session, _cliente: {
            "weekly_url": "https://app.example.com/client-checks/weekly/abc",
            "monthly_url": "https://app.example.com/client-checks/dca/xyz",
            "check_portal_url": "https://app.example.com/check",
        },
    )
    monkeypatch.setattr(services, "_resolve_package_name", lambda _c: "Pacchetto Gold")
    monkeypatch.setattr(services, "build_hm_wa_link", lambda _c, _hm: "https://wa.me/390000000")

    captured_template = {}

    def _fake_render_template(_tpl, **kwargs):
        captured_template.update(kwargs)
        return "<html>recap+check+whatsapp</html>"

    monkeypatch.setattr(services, "render_template", _fake_render_template)

    def _fake_send(msg):
        sent["count"] += 1
        sent["html"] = msg.html
        sent["subject"] = msg.subject
        sent["to"] = msg.recipients

    monkeypatch.setattr(mail, "send", _fake_send)

    with app.app_context():
        ok = services.send_onboarding_email(cliente.cliente_id)

    assert ok is True
    assert sent["count"] == 1
    assert sent["html"] == "<html>recap+check+whatsapp</html>"
    assert sent["to"] == ["mario@example.com"]
    assert captured_template["package_name"] == "Pacchetto Gold"
    assert captured_template["weekly_check_url"] is not None
    assert captured_template["monthly_check_url"] is not None
    assert captured_template["whatsapp_url"] == "https://wa.me/390000000"
    assert cliente.onboarding_email_sent_at is not None
    assert fake_session.committed is True


def test_send_onboarding_email_is_idempotent(monkeypatch) -> None:
    app = Flask(__name__)
    app.config["MAIL_SERVER"] = "smtp.test.local"

    cliente = SimpleNamespace(
        cliente_id=202,
        nome_cognome="Giulia Bianchi",
        mail="giulia@example.com",
        onboarding_email_sent_at="already-sent",
        health_manager_user=None,
    )
    fake_session = _FakeSession(cliente)

    monkeypatch.setattr(services.db, "session", fake_session)

    called = {"send": 0}
    monkeypatch.setattr(mail, "send", lambda _msg: called.__setitem__("send", called["send"] + 1))

    with app.app_context():
        ok = services.send_onboarding_email(cliente.cliente_id)

    assert ok is False
    assert called["send"] == 0
    assert fake_session.committed is False
