"""
Celery application instance for corposostenibile.

This module exports the Celery instance that is configured in extensions.py
to make it accessible for the Celery worker and beat processes.
"""
from corposostenibile.extensions import celery

# Import all tasks to register them with Celery
from corposostenibile.blueprints.respond_io import followup_tasks, tasks
from corposostenibile.blueprints.respond_io import pre_assignment_tasks

# Export celery instance
__all__ = ['celery']