"""Conftest minimo per test unitari che non richiedono DB."""
import pytest
from flask import Flask


@pytest.fixture
def app_context():
    """Fornisce app context per test che usano current_app (es. logger)."""
    app = Flask(__name__)
    with app.app_context():
        yield
