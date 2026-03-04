"""
Celery application instance for corposostenibile.

This module exports the Celery instance that is configured in extensions.py
to make it accessible for the Celery worker and beat processes.

Calling create_app() is required so that init_extensions() configures
the Celery instance with the Flask app context (_ContextTask).
"""
from corposostenibile import create_app
from corposostenibile.extensions import celery

# Initialise Flask app so that Celery tasks run inside an app context
flask_app = create_app()

# Import all tasks to register them with Celery
from corposostenibile.blueprints.respond_io import followup_tasks, tasks  # noqa: E402
from corposostenibile.blueprints.respond_io import pre_assignment_tasks  # noqa: E402
from corposostenibile.blueprints.respond_io import webhook_tasks  # noqa: E402
from corposostenibile.blueprints.tasks import tasks as general_tasks  # noqa: E402

# Export celery instance
__all__ = ['celery']