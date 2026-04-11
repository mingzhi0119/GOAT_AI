from __future__ import annotations

from fastapi import BackgroundTasks

from backend.services.background_jobs import (
    FastAPIBackgroundJobRunner,
    ThreadBackgroundJobRunner,
)


def test_fastapi_background_job_runner_enqueues_named_job() -> None:
    background_tasks = BackgroundTasks()
    runner = FastAPIBackgroundJobRunner(background_tasks=background_tasks)
    calls: list[tuple[str, int]] = []

    def job(*, name: str, count: int) -> None:
        calls.append((name, count))

    runner.submit(
        name="upload-postprocess",
        target=job,
        kwargs={"name": "queued", "count": 2},
    )

    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    task.func(**task.kwargs)
    assert calls == [("queued", 2)]


def test_thread_background_job_runner_starts_named_thread(monkeypatch) -> None:
    started: list[dict[str, object]] = []

    class _FakeThread:
        def __init__(
            self,
            *,
            name: str,
            target,
            kwargs,
            daemon: bool,
        ) -> None:
            self.name = name
            self.target = target
            self.kwargs = kwargs
            self.daemon = daemon

        def start(self) -> None:
            started.append(
                {
                    "name": self.name,
                    "kwargs": dict(self.kwargs),
                    "daemon": self.daemon,
                }
            )
            self.target(**self.kwargs)

    calls: list[str] = []
    monkeypatch.setattr(
        "backend.services.background_jobs.threading.Thread",
        _FakeThread,
    )
    runner = ThreadBackgroundJobRunner(daemon=False)

    runner.submit(
        name="code-sandbox-recovery",
        target=lambda *, task_id: calls.append(task_id),
        kwargs={"task_id": "cs-1"},
    )

    assert started == [
        {
            "name": "code-sandbox-recovery",
            "kwargs": {"task_id": "cs-1"},
            "daemon": False,
        }
    ]
    assert calls == ["cs-1"]
