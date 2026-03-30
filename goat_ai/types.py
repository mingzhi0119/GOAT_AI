"""Shared typing for chat turns and uploads (no Streamlit imports)."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ChatTurn(TypedDict):
    """One message in the in-memory conversation (user or assistant)."""

    role: str
    content: str


class TabularUploadLike(Protocol):
    """Streamlit UploadedFile–compatible surface for validation/parsing."""

    name: str
    size: int
