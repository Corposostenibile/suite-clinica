"""
Test per l'invio email riepilogo check settimanale al cliente.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def app_context():
    """Fornisce app context per test che usano current_app."""
    try:
        from corposostenibile import create_app
        app = create_app("testing")
    except Exception:
        app = __import__("flask").Flask(__name__)
    with app.app_context():
        yield


class TestSendWeeklyCheckSummaryToClient:
    """Test NotificationService.send_weekly_check_summary_to_client."""

    @patch("corposostenibile.blueprints.auth.email_utils.send_mail_html")
    @patch("flask.render_template")
    @patch("corposostenibile.blueprints.client_checks.services.WeeklyCheckResponse")
    def test_send_weekly_check_summary_calls_send_mail_html(
        self, mock_wcr_class, mock_render, mock_send_mail, app_context
    ):
        """Verifica che con una response valida venga chiamato send_mail_html con subject e recipient corretti."""
        from corposostenibile.blueprints.client_checks.services import NotificationService

        # Mock response: assignment -> cliente con mail
        mock_cliente = MagicMock()
        mock_cliente.nome_cognome = "Mario Rossi"
        mock_cliente.cliente_id = 1
        mock_cliente.mail = "cliente@example.com"

        mock_assignment = MagicMock()
        mock_assignment.cliente = mock_cliente

        mock_response = MagicMock()
        mock_response.id = 99
        mock_response.assignment = mock_assignment
        mock_response.submit_date = datetime(2025, 2, 2, 10, 30, 0)
        mock_response.what_worked = "Ho mangiato bene"
        mock_response.what_didnt_work = None
        mock_response.what_learned = None
        mock_response.what_focus_next = None
        mock_response.injuries_notes = None
        mock_response.digestion_rating = 8
        mock_response.energy_rating = None
        mock_response.strength_rating = None
        mock_response.hunger_rating = None
        mock_response.sleep_rating = None
        mock_response.mood_rating = None
        mock_response.motivation_rating = None
        mock_response.weight = None
        mock_response.nutrition_program_adherence = None
        mock_response.training_program_adherence = None
        mock_response.exercise_modifications = None
        mock_response.daily_steps = None
        mock_response.completed_training_weeks = None
        mock_response.planned_training_days = None
        mock_response.live_session_topics = None
        mock_response.nutritionist_rating = None
        mock_response.nutritionist_feedback = None
        mock_response.psychologist_rating = None
        mock_response.psychologist_feedback = None
        mock_response.coach_rating = None
        mock_response.coach_feedback = None
        mock_response.progress_rating = None
        mock_response.referral = None
        mock_response.extra_comments = None
        mock_response.photo_front = None
        mock_response.photo_side = None
        mock_response.photo_back = None

        mock_render.return_value = "<html>Riepilogo</html>"

        # isinstance(response, WeeklyCheckResponse) deve essere True
        mock_wcr_class.__class__ = type  # per evitare problemi con isinstance
        with patch(
            "corposostenibile.blueprints.client_checks.services.isinstance",
            return_value=True,
        ):
            NotificationService.send_weekly_check_summary_to_client(mock_response)

        mock_send_mail.assert_called_once()
        call_kw = mock_send_mail.call_args
        assert call_kw[1]["recipients"] == ["cliente@example.com"]
        assert "Riepilogo" in call_kw[1]["subject"]
        assert "02/02/2025" in call_kw[1]["subject"] or "2025" in call_kw[1]["subject"]
        assert call_kw[1]["html_body"] == "<html>Riepilogo</html>"
        assert call_kw[1]["text_body"]

    @patch("corposostenibile.blueprints.auth.email_utils.send_mail_html")
    @patch("corposostenibile.blueprints.client_checks.services.WeeklyCheckResponse")
    def test_send_weekly_check_summary_skips_if_no_mail(
        self, mock_wcr_class, mock_send_mail, app_context
    ):
        """Se il cliente non ha mail, send_mail_html non viene chiamato."""
        from corposostenibile.blueprints.client_checks.services import NotificationService

        mock_cliente = MagicMock()
        mock_cliente.nome_cognome = "Senza Email"
        mock_cliente.cliente_id = 2
        mock_cliente.mail = None

        mock_assignment = MagicMock()
        mock_assignment.cliente = mock_cliente

        mock_response = MagicMock()
        mock_response.id = 88
        mock_response.assignment = mock_assignment

        with patch(
            "corposostenibile.blueprints.client_checks.services.isinstance",
            return_value=True,
        ):
            NotificationService.send_weekly_check_summary_to_client(mock_response)

        mock_send_mail.assert_not_called()

    @patch("corposostenibile.blueprints.auth.email_utils.send_mail_html")
    def test_send_weekly_check_summary_skips_if_not_weekly_check_response(
        self, mock_send_mail, app_context
    ):
        """Se l'oggetto non è WeeklyCheckResponse, send_mail_html non viene chiamato."""
        from corposostenibile.blueprints.client_checks.services import NotificationService

        with patch(
            "corposostenibile.blueprints.client_checks.services.isinstance",
            return_value=False,
        ):
            NotificationService.send_weekly_check_summary_to_client(MagicMock())

        mock_send_mail.assert_not_called()
