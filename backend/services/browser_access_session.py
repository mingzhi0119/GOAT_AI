from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import Response

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.domain.rate_limit_policy import RateLimitPolicy
from backend.domain.scope_catalog import FULL_SCOPES
from backend.services.rate_limiter import StoredSlidingWindowRateLimiter
from backend.services.rate_limit_store import InMemorySlidingWindowRateLimitStore
from goat_ai.config.settings import Settings

_COOKIE_NAME = "goat_access_session"
_AUTH_MODE = "shared_access_cookie_v1"
_DEFAULT_TENANT_ID = "tenant:default"
_LOGIN_RATE_LIMITER = StoredSlidingWindowRateLimiter(
    policy=RateLimitPolicy(window_sec=300, max_requests=10),
    store=InMemorySlidingWindowRateLimitStore(),
)


@dataclass(frozen=True)
class SharedAccessSession:
    owner_id: str
    principal_id: str
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class SharedAccessLoginAttemptDecision:
    allowed: bool
    retry_after: int = 0


def shared_access_cookie_name() -> str:
    return _COOKIE_NAME


def shared_access_enabled(settings: Settings) -> bool:
    return settings.shared_access_enabled


def issue_shared_access_session(
    settings: Settings, *, now: datetime | None = None
) -> SharedAccessSession:
    current = _coerce_utc(now)
    session_uuid = str(uuid4())
    return SharedAccessSession(
        owner_id=session_uuid,
        principal_id=f"principal:browser:{session_uuid}",
        issued_at=current.isoformat(),
        expires_at=(
            current + timedelta(seconds=settings.shared_access_session_ttl_sec)
        ).isoformat(),
    )


def build_shared_access_authorization_context(
    session: SharedAccessSession,
) -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId(session.principal_id),
        tenant_id=TenantId(_DEFAULT_TENANT_ID),
        scopes=FULL_SCOPES,
        credential_id=f"credential:shared-access:{session.owner_id}",
        legacy_owner_id=session.owner_id,
        auth_mode=_AUTH_MODE,
    )


def set_shared_access_cookie(
    response: Response,
    *,
    session: SharedAccessSession,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=_COOKIE_NAME,
        value=encode_shared_access_session(session=session, settings=settings),
        max_age=settings.shared_access_session_ttl_sec,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_shared_access_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def read_shared_access_session_from_request(
    request: Request, *, settings: Settings, now: datetime | None = None
) -> SharedAccessSession | None:
    raw = (request.cookies.get(_COOKIE_NAME) or "").strip()
    if not raw or not shared_access_enabled(settings):
        return None
    return decode_shared_access_session(raw, settings=settings, now=now)


def encode_shared_access_session(
    *, session: SharedAccessSession, settings: Settings
) -> str:
    payload = {
        "owner_id": session.owner_id,
        "principal_id": session.principal_id,
        "issued_at": session.issued_at,
        "expires_at": session.expires_at,
    }
    encoded_payload = _b64_encode(
        json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    )
    signature = _sign_shared_access_payload(encoded_payload, settings=settings)
    return f"{encoded_payload}.{signature}"


def decode_shared_access_session(
    raw: str, *, settings: Settings, now: datetime | None = None
) -> SharedAccessSession | None:
    try:
        encoded_payload, encoded_signature = raw.split(".", 1)
    except ValueError:
        return None
    expected_signature = _sign_shared_access_payload(encoded_payload, settings=settings)
    if not hmac.compare_digest(encoded_signature, expected_signature):
        return None
    try:
        payload = json.loads(_b64_decode(encoded_payload).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    owner_id = str(payload.get("owner_id", "")).strip()
    principal_id = str(payload.get("principal_id", "")).strip()
    issued_at = str(payload.get("issued_at", "")).strip()
    expires_at = str(payload.get("expires_at", "")).strip()
    if not owner_id or not principal_id or not issued_at or not expires_at:
        return None
    issued_dt = _parse_utc_timestamp(issued_at)
    expires_dt = _parse_utc_timestamp(expires_at)
    if issued_dt is None or expires_dt is None or expires_dt <= issued_dt:
        return None
    if expires_dt <= _coerce_utc(now):
        return None
    return SharedAccessSession(
        owner_id=owner_id,
        principal_id=principal_id,
        issued_at=issued_dt.isoformat(),
        expires_at=expires_dt.isoformat(),
    )


def evaluate_shared_access_login_attempt(
    request: Request,
) -> SharedAccessLoginAttemptDecision:
    subject = {
        "route_group": "/api/auth/login",
        "client": _request_client_identity(request),
    }
    decision = _LOGIN_RATE_LIMITER.evaluate(subject=subject, now=time.monotonic())
    return SharedAccessLoginAttemptDecision(
        allowed=decision.allowed,
        retry_after=decision.retry_after,
    )


def _request_client_identity(request: Request) -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            return candidate
    client = request.client
    if client is not None and client.host:
        return client.host
    return "unknown"


def _sign_shared_access_payload(encoded_payload: str, *, settings: Settings) -> str:
    digest = hmac.new(
        settings.shared_access_session_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64_encode(digest)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


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
