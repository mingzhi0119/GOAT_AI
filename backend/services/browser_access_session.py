from __future__ import annotations

import hmac
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from itsdangerous import BadData, URLSafeTimedSerializer
from itsdangerous.timed import TimestampSigner
from starlette.requests import Request
from starlette.responses import Response

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.domain.rate_limit_policy import RateLimitPolicy
from backend.domain.scope_catalog import FULL_SCOPES
from backend.services.rate_limiter import StoredSlidingWindowRateLimiter
from backend.services.rate_limit_store import InMemorySlidingWindowRateLimitStore
from backend.services.password_hashing import hash_password, verify_password
from goat_ai.config.settings import Settings

_COOKIE_NAME = "goat_access_session"
_AUTH_MODE = "shared_access_cookie_v1"
_DEFAULT_TENANT_ID = "tenant:default"
_COOKIE_SERIALIZER_SALT = "goat.shared-access.cookie"
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


class _SharedAccessTimestampSigner(TimestampSigner):
    def __init__(
        self,
        *args: object,
        current_time: datetime | None = None,
        **kwargs: object,
    ) -> None:
        self._current_time = current_time
        super().__init__(*args, **kwargs)

    def get_timestamp(self) -> int:
        if self._current_time is None:
            return super().get_timestamp()
        return int(_coerce_utc(self._current_time).timestamp())


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
    return _shared_access_serializer(
        settings,
        now=_parse_utc_timestamp(session.issued_at),
    ).dumps(payload)


def verify_shared_access_password(settings: Settings, *, password: str) -> bool:
    candidate = password.strip()
    password_hash = settings.shared_access_password_hash.strip()
    if password_hash:
        return verify_password(candidate, password_hash)
    return hmac.compare_digest(candidate, settings.shared_access_password.strip())


def hash_shared_access_password(password: str) -> str:
    return hash_password(password.strip())


def decode_shared_access_session(
    raw: str, *, settings: Settings, now: datetime | None = None
) -> SharedAccessSession | None:
    try:
        payload = _shared_access_serializer(settings, now=now).loads(
            raw,
            max_age=settings.shared_access_session_ttl_sec,
        )
    except BadData:
        return None
    if not isinstance(payload, dict):
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


def _shared_access_serializer(
    settings: Settings, *, now: datetime | None = None
) -> URLSafeTimedSerializer:
    signer_kwargs: dict[str, object] = {}
    if now is not None:
        signer_kwargs["current_time"] = now
    return URLSafeTimedSerializer(
        secret_key=settings.shared_access_session_secret,
        salt=_COOKIE_SERIALIZER_SALT,
        signer=_SharedAccessTimestampSigner,
        signer_kwargs=signer_kwargs,
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
