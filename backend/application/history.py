"""History sidebar use cases — read paths over SessionRepository."""
from __future__ import annotations

from backend.services.chat_runtime import SessionRepository, SessionSummaryRecord


def list_session_summaries(
    repository: SessionRepository,
    owner_filter: str | None = None,
) -> list[SessionSummaryRecord]:
    """Return persisted session metadata rows for the history sidebar."""
    return repository.list_sessions(owner_filter=owner_filter)


def delete_all_sessions_for_owner(
    repository: SessionRepository,
    owner_filter: str | None,
) -> None:
    """Delete sessions scoped to one owner when filtering is enabled."""
    repository.delete_all_sessions(owner_filter=owner_filter)
