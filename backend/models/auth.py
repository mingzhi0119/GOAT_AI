"""Pydantic schemas for shared browser-access authentication."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SharedAccessSessionResponse(BaseModel):
    """Browser-session status for the public shared-password gate."""

    auth_required: bool
    authenticated: bool
    expires_at: str | None = None


class SharedAccessLoginRequest(BaseModel):
    """Password payload for POST /api/auth/login."""

    password: str = Field(..., min_length=1, max_length=512)
