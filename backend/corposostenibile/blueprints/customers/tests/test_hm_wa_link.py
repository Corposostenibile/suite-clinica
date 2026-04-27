from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import quote

from flask import Flask

from corposostenibile.blueprints.customers.services import build_hm_wa_link


def test_build_hm_wa_link_normalizes_number_and_encodes_message() -> None:
    app = Flask(__name__)
    app.config["WHATSAPP_BUSINESS_NUMBER"] = "+39 333 12 34 567"

    cliente = SimpleNamespace(nome_cognome="Mario Rossi")
    hm = SimpleNamespace(first_name="Anna", last_name="Verdi")

    expected_message = (
        "Ciao, sono Mario Rossi. "
        "Mi e stata assegnata Anna Verdi come Health Manager."
    )

    with app.app_context():
        link = build_hm_wa_link(cliente, hm)

    assert link.startswith("https://wa.me/393331234567?text=")
    assert "+" not in link.split("/", 3)[3].split("?", 1)[0]
    assert quote(expected_message, safe="") in link
