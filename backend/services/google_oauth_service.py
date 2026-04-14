from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
from urllib.parse import urlencode

from itsdangerous import BadData, URLSafeTimedSerializer
import requests
from starlette.responses import Response

from goat_ai.config.settings import Settings

_GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_STATE_COOKIE_NAME = "goat_google_oauth_state"
_STATE_SERIALIZER_SALT = "goat.google-oauth.state"
_ALLOWED_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


@dataclass(frozen=True)
class GoogleOAuthState:
    state: str
    expires_at: str


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    display_name: str


class GoogleOAuthError(RuntimeError):
    pass


class InvalidGoogleStateError(GoogleOAuthError):
    pass


class InvalidGoogleTokenError(GoogleOAuthError):
    pass


def google_oauth_enabled(settings: Settings) -> bool:
    return settings.google_oauth_enabled


def google_oauth_state_cookie_name() -> str:
    return _STATE_COOKIE_NAME


def issue_google_oauth_state(
    settings: Settings,
    *,
    now: datetime | None = None,
) -> GoogleOAuthState:
    current = _coerce_utc(now)
    return GoogleOAuthState(
        state=secrets.token_urlsafe(24),
        expires_at=(
            current + timedelta(seconds=settings.google_oauth_state_ttl_sec)
        ).isoformat(),
    )


def build_google_oauth_authorization_url(
    settings: Settings,
    *,
    state: str,
) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{_GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


def set_google_oauth_state_cookie(
    response: Response,
    *,
    oauth_state: GoogleOAuthState,
    settings: Settings,
) -> None:
    payload = {
        "state": oauth_state.state,
        "expires_at": oauth_state.expires_at,
    }
    response.set_cookie(
        key=_STATE_COOKIE_NAME,
        value=_state_serializer(settings).dumps(payload),
        max_age=settings.google_oauth_state_ttl_sec,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_google_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_STATE_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def validate_google_oauth_state(
    *,
    cookie_value: str,
    state: str,
    settings: Settings,
    now: datetime | None = None,
) -> None:
    if not cookie_value.strip() or not state.strip():
        raise InvalidGoogleStateError("Google login state is missing.")
    try:
        payload = _state_serializer(settings).loads(
            cookie_value,
            max_age=settings.google_oauth_state_ttl_sec,
        )
    except BadData as exc:
        raise InvalidGoogleStateError("Google login state is invalid.") from exc
    if not isinstance(payload, dict):
        raise InvalidGoogleStateError("Google login state is invalid.")
    expected_state = str(payload.get("state", "")).strip()
    expires_at = str(payload.get("expires_at", "")).strip()
    expires_dt = _parse_utc_timestamp(expires_at)
    if (
        expected_state != state.strip()
        or expires_dt is None
        or expires_dt <= _coerce_utc(now)
    ):
        raise InvalidGoogleStateError("Google login state is invalid.")


def exchange_google_code_for_identity(
    settings: Settings,
    *,
    code: str,
    timeout_sec: float = 10.0,
    now: datetime | None = None,
) -> GoogleIdentity:
    token_response = requests.post(
        _GOOGLE_TOKEN_URL,
        data={
            "code": code.strip(),
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=timeout_sec,
    )
    if token_response.status_code != 200:
        raise InvalidGoogleTokenError("Google login token exchange failed.")
    payload = token_response.json()
    id_token = str(payload.get("id_token", "")).strip()
    if not id_token:
        raise InvalidGoogleTokenError("Google login token exchange failed.")

    tokeninfo = requests.get(
        _GOOGLE_TOKENINFO_URL,
        params={"id_token": id_token},
        timeout=timeout_sec,
    )
    if tokeninfo.status_code != 200:
        raise InvalidGoogleTokenError("Google login token validation failed.")
    info = tokeninfo.json()
    aud = str(info.get("aud", "")).strip()
    iss = str(info.get("iss", "")).strip()
    email = str(info.get("email", "")).strip().lower()
    subject = str(info.get("sub", "")).strip()
    display_name = str(info.get("name", "")).strip()
    exp = str(info.get("exp", "")).strip()
    email_verified = str(info.get("email_verified", "")).strip().lower()
    if (
        aud != settings.google_client_id
        or iss not in _ALLOWED_ISSUERS
        or not email
        or not subject
        or email_verified not in {"true", "1"}
    ):
        raise InvalidGoogleTokenError("Google login token validation failed.")
    try:
        exp_ts = int(exp)
    except ValueError as exc:
        raise InvalidGoogleTokenError("Google login token validation failed.") from exc
    if exp_ts <= int(_coerce_utc(now).timestamp()):
        raise InvalidGoogleTokenError("Google login token validation failed.")
    if not display_name:
        display_name = email.split("@", 1)[0]
    return GoogleIdentity(
        subject=subject,
        email=email,
        display_name=display_name,
    )


def _state_serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        secret_key=settings.browser_session_secret,
        salt=_STATE_SERIALIZER_SALT,
    )


def _coerce_utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _parse_utc_timestamp(raw: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)
