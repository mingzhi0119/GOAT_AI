"""Replaceable background job runners for durable in-process execution paths."""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class BackgroundJobRunner(Protocol):
    """Minimal boundary for fire-and-forget task scheduling."""

    def submit(
        self,
        *,
        name: str,
        target: Callable[..., Any],
        kwargs: Mapping[str, Any] | None = None,
    ) -> None: ...


class SupportsAddTask(Protocol):
    def add_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any: ...


@dataclass
class FastAPIBackgroundJobRunner:
    """Schedule work through FastAPI BackgroundTasks."""

    background_tasks: SupportsAddTask

    def submit(
        self,
        *,
        name: str,
        target: Callable[..., Any],
        kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        _ = name
        self.background_tasks.add_task(target, **dict(kwargs or {}))


@dataclass
class ThreadBackgroundJobRunner:
    """Schedule work on daemon threads for process-local async execution."""

    daemon: bool = True

    def submit(
        self,
        *,
        name: str,
        target: Callable[..., Any],
        kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        thread = threading.Thread(
            name=name,
            target=target,
            kwargs=dict(kwargs or {}),
            daemon=self.daemon,
        )
        thread.start()
