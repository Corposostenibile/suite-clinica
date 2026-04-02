"""
test_api_list_eager_load.py
============================

Verifica che GET /api/customers NON esegua query N+1 per le relazioni
`subscriptions` e `consulenti_multipli` dei clienti.

Problema rilevato
-----------------
`_DEFAULT_EAGER_LOAD` nel repository non includeva `subscriptions` né
`consulenti_multipli`, entrambe presenti in `ClienteSchema`. SQLAlchemy
le caricava in lazy-load: una query per ogni cliente nella pagina.

Con 50 clienti per pagina → fino a 100 query lazy in più per chiamata.

Fix applicata
-------------
Aggiunti `selectinload(Cliente.subscriptions)` e
`selectinload(Cliente.consulenti_multipli)` a `_DEFAULT_EAGER_LOAD`.
Cambiato anche `subqueryload(Cliente.cartelle)` → `selectinload`.

Come eseguire
-------------
    cd backend
    pytest corposostenibile/blueprints/customers/tests/test_api_list_eager_load.py -v
"""
from __future__ import annotations

import pytest
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.engine import Engine

from corposostenibile import create_app


# ─────────────────────────── fixtures ────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    application = create_app("development")
    with application.app_context():
        yield application


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def admin_client(app, client):
    """Client autenticato come admin."""
    with app.app_context():
        from corposostenibile.models import User
        admin = User.query.filter_by(email="admin1@suiteclinica.com").first()
        assert admin is not None, "Utente admin non trovato nel DB di sviluppo"

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

    return client


# ─────────────────────────── query counter ───────────────────────────────────

@contextmanager
def count_queries():
    """
    Conta le query SQL eseguite nel blocco.
    Stessa implementazione di test_get_teams_eager_load.py — vedi lì
    per la spiegazione del meccanismo.
    """
    counter = {"count": 0, "statements": []}

    def before_execute(conn, cursor, statement, parameters, context, executemany):
        counter["count"] += 1
        counter["statements"].append(statement.strip()[:120])

    event.listen(Engine, "before_cursor_execute", before_execute)
    try:
        yield counter
    finally:
        event.remove(Engine, "before_cursor_execute", before_execute)


# ─────────────────────────── test principali ─────────────────────────────────

class TestApiListQueryCount:
    """Verifica che la lista clienti non generi query N+1 sulle relazioni."""

    # Header JSON necessario: il test client invia Accept: */* di default,
    # il che attiva la SPA fallback (serve index.html). Con application/json
    # Flask bypassa il SPA handler e raggiunge gli endpoint API.
    _JSON = {"Accept": "application/json"}
    _BASE = "/api/v1/customers/"

    def test_endpoint_risponde_200(self, admin_client):
        """Smoke test."""
        resp = admin_client.get(self._BASE + "?per_page=10", headers=self._JSON)
        assert resp.status_code == 200, f"Status inatteso: {resp.status_code} — {resp.data[:200]}"

    def test_risposta_contiene_campi_attesi(self, admin_client):
        """La struttura JSON non è cambiata dopo la fix."""
        resp = admin_client.get(self._BASE + "?per_page=10", headers=self._JSON)
        data = resp.get_json()

        assert "data" in data, f"Chiave 'data' mancante. Chiavi presenti: {list(data.keys())}"
        assert "pagination" in data, "Chiave 'pagination' mancante"
        assert isinstance(data["data"], list)

    def test_subscriptions_presenti_nella_risposta(self, admin_client):
        """
        Ogni cliente ha il campo subscriptions serializzato.
        Se mancasse, la relazione non verrebbe serializzata e il problema
        di lazy-load sarebbe nascosto (ma ancora presente).
        """
        resp = admin_client.get(self._BASE + "?per_page=5", headers=self._JSON)
        data = resp.get_json()["data"]

        for cliente in data:
            assert "subscriptions" in cliente, (
                f"Campo 'subscriptions' mancante per cliente {cliente.get('cliente_id')}"
            )

    def test_professionisti_multipli_presenti(self, admin_client):
        """Relazioni professionisti_multipli presenti e come lista."""
        resp = admin_client.get(self._BASE + "?per_page=5", headers=self._JSON)
        data = resp.get_json()["data"]

        for cliente in data:
            for campo in ("nutrizionisti_multipli", "coaches_multipli", "psicologi_multipli"):
                assert campo in cliente, f"Campo '{campo}' mancante per cliente {cliente.get('cliente_id')}"
                assert isinstance(cliente[campo], list), f"'{campo}' dovrebbe essere una lista"

    def test_relazioni_caricate_eagerly(self, app):
        """
        Verifica DIRETTAMENTE che subscriptions e consulenti_multipli siano
        caricati in modo eager — la stessa tecnica usata per Team.members.

        Dopo aver eseguito la query con _DEFAULT_EAGER_LOAD, accedere a
        cliente.subscriptions NON deve emettere query aggiuntive.
        """
        from corposostenibile.models import Cliente
        from corposostenibile.blueprints.customers.repository import _DEFAULT_EAGER_LOAD

        with app.app_context():
            clienti = (
                Cliente.query
                .filter(Cliente.show_in_clienti_lista.is_(True))
                .options(*_DEFAULT_EAGER_LOAD)
                .limit(5)
                .all()
            )

            for cliente in clienti:
                # Accedere a .subscriptions e .consulenti_multipli NON deve emettere query
                with count_queries() as counter:
                    _ = list(cliente.subscriptions)
                    _ = list(cliente.consulenti_multipli)

                assert counter["count"] == 0, (
                    f"Cliente {cliente.cliente_id}: accedere a relazioni eager ha emesso "
                    f"{counter['count']} query — il selectinload non ha funzionato.\n"
                    f"Query: {counter['statements']}"
                )

    def test_query_count_non_scala_con_per_page(self, admin_client, app):
        """
        La prova definitiva del N+1: il numero di query deve restare
        pressoché uguale indipendentemente da per_page=5 vs per_page=20.

        Con N+1, per_page=20 avrebbe ~30 query in più rispetto a per_page=5
        (2 relazioni lazy × 15 clienti extra = 30).
        Con eager load, la differenza deve essere < 5.
        """
        with app.app_context():
            with count_queries() as small:
                admin_client.get(self._BASE + "?per_page=5", headers=self._JSON)

        with app.app_context():
            with count_queries() as large:
                admin_client.get(self._BASE + "?per_page=20", headers=self._JSON)

        print(f"\n  Query per per_page=5:  {small['count']}")
        print(f"  Query per per_page=20: {large['count']}")

        diff = large["count"] - small["count"]
        assert diff < 5, (
            f"Il numero di query scala con per_page "
            f"(+{diff} passando da 5 a 20 clienti) — N+1 ancora presente"
        )
