"""Pydantic schemas for browser authentication."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BrowserLoginMethod = Literal["shared_password", "account_password", "google"]
AccountProvider = Literal["local", "google"]


class AuthenticatedBrowserUser(BaseModel):
    id: str
    email: str
    display_name: str
    provider: AccountProvider


class BrowserAuthSessionResponse(BaseModel):
    """Browser-session status for shared-password and account auth."""

    auth_required: bool
    authenticated: bool
    expires_at: str | None = None
    available_login_methods: list[BrowserLoginMethod] = Field(default_factory=list)
    active_login_method: BrowserLoginMethod | None = None
    user: AuthenticatedBrowserUser | None = None


class SharedAccessLoginRequest(BaseModel):
    """Password payload for POST /api/auth/login."""

    password: str = Field(..., min_length=1, max_length=512)


class AccountLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=512)


class GoogleOAuthUrlResponse(BaseModel):
    authorization_url: str
    state_expires_at: str


class GoogleOAuthLoginRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=4096)
    state: str = Field(..., min_length=1, max_length=1024)
