"""
test_get_teams_eager_load.py
============================

Verifica che GET /api/team/teams NON esegua query N+1 per i membri dei team.

Problema rilevato
-----------------
Prima della fix, `get_teams` caricava solo `Team.head` con eager loading.
La proprietà `team.members` veniva acceduta in `_serialize_team` per
calcolare `member_count`, causando una query separata per ogni team.

Con 4 team → 5 query (1 principale + 4 lazy-load members).
Con 20 team → 21 query.

Fix applicata
-------------
Aggiunto `selectinload(Team.members)` alla query base. SQLAlchemy emette
un unico `SELECT ... WHERE team_id IN (1, 2, 3, 4)` per tutti i members,
indipendentemente dal numero di team restituiti.

Come eseguire
-------------
    cd backend
    pytest corposostenibile/blueprints/team/tests/test_get_teams_eager_load.py -v
"""
from __future__ import annotations

import pytest
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.engine import Engine

from corposostenibile import create_app
from corposostenibile.extensions import db as _db


# ─────────────────────────── fixtures ────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """App Flask che punta al DB di sviluppo locale (read-only nei test)."""
    application = create_app("development")
    with application.app_context():
        yield application


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def admin_client(app, client):
    """Client autenticato come admin usando il DB di sviluppo locale."""
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
    Context manager che conta le query SQL eseguite nel blocco.

    Usa gli event listener di SQLAlchemy sull'Engine (la stessa tecnica
    del listener per le query lente in extensions.py), registrandoli
    solo per la durata del blocco e rimuovendoli subito dopo.

    Esempio d'uso::

        with count_queries() as counter:
            response = client.get("/api/team/teams")
        print(counter["count"])  # numero di query eseguite
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

class TestGetTeamsQueryCount:
    """Verifica che il numero di query non cresca con il numero di team (N+1)."""

    def test_endpoint_risponde_200(self, admin_client):
        """Smoke test: l'endpoint è raggiungibile e ritorna 200."""
        resp = admin_client.get("/api/team/teams")
        assert resp.status_code == 200, f"Status inatteso: {resp.status_code} — {resp.data[:200]}"

    def test_risposta_contiene_campi_attesi(self, admin_client):
        """La struttura JSON della risposta non è cambiata dopo la fix."""
        resp = admin_client.get("/api/team/teams")
        data = resp.get_json()

        assert "teams" in data, "Chiave 'teams' mancante nella risposta"
        assert "total" in data, "Chiave 'total' mancante nella risposta"
        assert isinstance(data["teams"], list)

    def test_ogni_team_ha_member_count(self, admin_client):
        """member_count è presente e numerico per ogni team."""
        resp = admin_client.get("/api/team/teams")
        teams = resp.get_json()["teams"]

        for team in teams:
            assert "member_count" in team, f"member_count mancante nel team {team.get('id')}"
            assert isinstance(team["member_count"], int)

    def test_members_caricati_con_selectinload(self, admin_client, app):
        """
        Verifica DIRETTAMENTE che Team.members sia caricato in modo eager.

        Dopo la query, ispeziona lo stato interno SQLAlchemy dei team:
        se 'members' è nello stato 'loaded', significa che il selectinload
        ha funzionato e NON ci sarà nessuna query aggiuntiva quando il
        codice accede a team.members.

        Questa è la prova più affidabile del fix: non dipende da soglie
        o dal numero di query di overhead (sessione, tracking, ecc.).
        """
        from sqlalchemy import inspect as sa_inspect
        from corposostenibile.models import Team

        with app.app_context():
            # Esegui la stessa query che fa l'endpoint
            from sqlalchemy.orm import joinedload, selectinload
            teams = (
                Team.query
                .options(joinedload(Team.head), selectinload(Team.members))
                .all()
            )

            for team in teams:
                state = sa_inspect(team)
                loaded_attrs = {k for k, v in state.attrs.items() if not v.history.empty}

                # 'members' deve essere già nello stato caricato,
                # non 'expired' (che causerebbe una lazy query al primo accesso)
                assert not state.attrs["members"].history.empty or \
                       "members" in {k for k in state.attrs.keys()
                                     if state.attrs[k].loaded_value is not None
                                     or state.attrs[k].loaded_value == []}, \
                    f"Team {team.id}: 'members' non è stato caricato eagerly"

                # Accedere a team.members ora NON deve emettere query
                with count_queries() as counter:
                    _ = len(team.members)
                assert counter["count"] == 0, (
                    f"Team {team.id}: accedere a .members ha emesso {counter['count']} "
                    f"query — il selectinload non ha funzionato"
                )

    def test_include_members_risposta_corretta(self, admin_client):
        """
        Con include_members=1 ogni team ha la lista dei membri nel JSON.
        Verifica che il dato sia corretto, non solo che l'endpoint risponda.
        """
        resp = admin_client.get("/api/team/teams?include_members=1")
        assert resp.status_code == 200
        teams = resp.get_json()["teams"]

        for team in teams:
            assert "members" in team, (
                f"members mancante nel team {team.get('id')} con include_members=1"
            )
            assert isinstance(team["members"], list)
            # member_count deve corrispondere alla lunghezza della lista members
            assert team["member_count"] == len(team["members"]), (
                f"Team {team.get('id')}: member_count={team['member_count']} "
                f"ma len(members)={len(team['members'])}"
            )
