"""Shared typing for chat turns and uploads."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ChatTurn(TypedDict):
    """One message in the in-memory conversation (user or assistant)."""

    role: str
    content: str


class TabularUploadLike(Protocol):
    """Minimal upload-like surface (name/size) for validation/parsing."""

    name: str
    size: int
