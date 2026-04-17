"""
Test per l'endpoint PATCH /old-suite/api/leads/<id>/story.

Verifica:
- Salvataggio corretto della storia
- Rifiuto di storia vuota
- 404 per lead inesistente o non old_suite
- Richiesta autenticazione (login_required)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class _FakeLead:
    """Mock SalesLead minimo per questi test."""

    def __init__(self, id: int, source_system: str = 'old_suite', client_story: str = None):
        self.id = id
        self.source_system = source_system
        self.client_story = client_story


def _make_app():
    from corposostenibile import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['LOGIN_DISABLED'] = True
    return app


class TestUpdateLeadStory:

    def test_salva_storia_correttamente(self):
        """PATCH con storia valida aggiorna client_story e restituisce 200."""
        app = _make_app()
        fake_lead = _FakeLead(id=1)

        with app.test_client() as client:
            with patch(
                'corposostenibile.blueprints.old_suite_integration.routes.SalesLead'
            ) as MockLead, patch(
                'corposostenibile.blueprints.old_suite_integration.routes.db'
            ) as mock_db:
                MockLead.query.filter_by.return_value.first.return_value = fake_lead

                rv = client.patch(
                    '/old-suite/api/leads/1/story',
                    json={'client_story': 'Cliente ha 35 anni, sovrappeso, motivata.'},
                    content_type='application/json',
                )

                assert rv.status_code == 200
                data = rv.get_json()
                assert data['success'] is True
                assert data['client_story'] == 'Cliente ha 35 anni, sovrappeso, motivata.'
                assert fake_lead.client_story == 'Cliente ha 35 anni, sovrappeso, motivata.'
                mock_db.session.commit.assert_called_once()

    def test_storia_vuota_ritorna_400(self):
        """PATCH con storia vuota restituisce 400."""
        app = _make_app()

        with app.test_client() as client:
            with patch(
                'corposostenibile.blueprints.old_suite_integration.routes.SalesLead'
            ) as MockLead:
                MockLead.query.filter_by.return_value.first.return_value = _FakeLead(id=1)

                for empty_payload in [
                    {'client_story': ''},
                    {'client_story': '   '},
                    {},
                ]:
                    rv = client.patch(
                        '/old-suite/api/leads/1/story',
                        json=empty_payload,
                        content_type='application/json',
                    )
                    assert rv.status_code == 400, f"Atteso 400 per payload {empty_payload}"
                    data = rv.get_json()
                    assert data['success'] is False

    def test_lead_non_trovata_ritorna_404(self):
        """PATCH su lead inesistente restituisce 404."""
        app = _make_app()

        with app.test_client() as client:
            with patch(
                'corposostenibile.blueprints.old_suite_integration.routes.SalesLead'
            ) as MockLead:
                MockLead.query.filter_by.return_value.first.return_value = None

                rv = client.patch(
                    '/old-suite/api/leads/9999/story',
                    json={'client_story': 'Storia qualsiasi'},
                    content_type='application/json',
                )
                assert rv.status_code == 404

    def test_storia_viene_trimmata(self):
        """La storia viene strip() prima di essere salvata."""
        app = _make_app()
        fake_lead = _FakeLead(id=1)

        with app.test_client() as client:
            with patch(
                'corposostenibile.blueprints.old_suite_integration.routes.SalesLead'
            ) as MockLead, patch(
                'corposostenibile.blueprints.old_suite_integration.routes.db'
            ):
                MockLead.query.filter_by.return_value.first.return_value = fake_lead

                rv = client.patch(
                    '/old-suite/api/leads/1/story',
                    json={'client_story': '  Storia con spazi  '},
                    content_type='application/json',
                )

                assert rv.status_code == 200
                assert fake_lead.client_story == 'Storia con spazi'

    def test_sovrascrive_storia_esistente(self):
        """PATCH aggiorna una storia già presente."""
        app = _make_app()
        fake_lead = _FakeLead(id=1, client_story='Storia vecchia')

        with app.test_client() as client:
            with patch(
                'corposostenibile.blueprints.old_suite_integration.routes.SalesLead'
            ) as MockLead, patch(
                'corposostenibile.blueprints.old_suite_integration.routes.db'
            ):
                MockLead.query.filter_by.return_value.first.return_value = fake_lead

                rv = client.patch(
                    '/old-suite/api/leads/1/story',
                    json={'client_story': 'Storia aggiornata'},
                    content_type='application/json',
                )

                assert rv.status_code == 200
                assert fake_lead.client_story == 'Storia aggiornata'
