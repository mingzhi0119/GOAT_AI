"""History sidebar use cases — read paths over SessionRepository."""
from __future__ import annotations

from backend.services.chat_runtime import SessionRepository, SessionSummaryRecord


def list_session_summaries(repository: SessionRepository) -> list[SessionSummaryRecord]:
    """Return persisted session metadata rows for the history sidebar."""
    return repository.list_sessions()
