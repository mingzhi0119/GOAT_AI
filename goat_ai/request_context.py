"""Per-request correlation id (async context); shared by logging and API errors."""
from __future__ import annotations

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("goat_request_id", default=None)


def get_request_id() -> str | None:
    """Return the active request id, if any."""
    return _request_id.get()


def set_request_id(value: str) -> Token[str | None]:
    """Bind ``value`` for the current async context; caller must reset when done."""
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous request id binding."""
    _request_id.reset(token)
