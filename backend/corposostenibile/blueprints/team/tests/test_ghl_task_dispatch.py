from __future__ import annotations

import os

os.environ.setdefault("FLASK_ENV", "testing")

from corposostenibile import create_app
from corposostenibile.blueprints.ghl_integration.routes import _dispatch_webhook_task


class _FakeTask:
    def __init__(self) -> None:
        self.called = None

    def apply(self, args=None, kwargs=None):
        self.called = ("apply", args, kwargs)
        return type("Result", (), {"id": "inline-task"})()

    def delay(self, *args, **kwargs):
        self.called = ("delay", args, kwargs)
        return type("Result", (), {"id": "queued-task"})()


def test_dispatch_executes_inline_in_testing_environment() -> None:
    app = create_app("testing")
    task = _FakeTask()
    payload = {"hello": "world"}

    with app.app_context():
        result = _dispatch_webhook_task(task, payload)

    assert result.id == "inline-task"
    assert task.called == ("apply", [payload], None)
