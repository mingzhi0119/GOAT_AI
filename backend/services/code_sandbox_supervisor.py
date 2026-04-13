"""In-process supervisor seam for sandbox execution lifecycle control."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol


class CodeSandboxExecutionSupervisor(Protocol):
    """Service-facing boundary for scheduling and canceling sandbox execution."""

    def register_execution(self, *, execution_id: str) -> Callable[[], bool]:
        """Return a callable that reports whether cancellation was requested."""

    def request_cancel(self, *, execution_id: str) -> None:
        """Mark an execution for cancellation."""

    def release_execution(self, *, execution_id: str) -> None:
        """Drop control state after execution reaches terminal state."""


class InProcessCodeSandboxSupervisor:
    """Track per-execution cancel tokens for in-process sandbox runs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancel_events: dict[str, threading.Event] = {}

    def register_execution(self, *, execution_id: str) -> Callable[[], bool]:
        """Return a callable that reports whether cancellation was requested."""
        with self._lock:
            event = self._cancel_events.setdefault(execution_id, threading.Event())
        return event.is_set

    def request_cancel(self, *, execution_id: str) -> None:
        """Mark one execution for cooperative cancellation."""
        with self._lock:
            event = self._cancel_events.setdefault(execution_id, threading.Event())
            event.set()

    def release_execution(self, *, execution_id: str) -> None:
        """Drop any in-memory control state after the run reaches a terminal state."""
        with self._lock:
            self._cancel_events.pop(execution_id, None)
