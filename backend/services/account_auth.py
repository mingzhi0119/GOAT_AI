from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets

from itsdangerous import BadData, URLSafeTimedSerializer
from starlette.requests import Request
from starlette.responses import Response

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.domain.rate_limit_policy import RateLimitPolicy
from backend.domain.scope_catalog import FULL_SCOPES
from backend.services.account_repository import (
    AccountProvider,
    AccountRepository,
    AccountUser,
    AccountUserIdentity,
    normalize_account_email,
)
from backend.services.password_hashing import verify_password
from backend.services.rate_limiter import StoredSlidingWindowRateLimiter
from backend.services.rate_limit_store import InMemorySlidingWindowRateLimitStore
from goat_ai.config.settings import Settings

_ACCOUNT_COOKIE_NAME = "goat_account_session"
_AUTH_MODE_LOCAL = "account_password_v1"
_AUTH_MODE_GOOGLE = "google_oauth_v1"
_COOKIE_SERIALIZER_SALT = "goat.account.cookie"
_DEFAULT_TENANT_ID = "tenant:default"
_LOGIN_RATE_LIMITER = StoredSlidingWindowRateLimiter(
    policy=RateLimitPolicy(window_sec=300, max_requests=10),
    store=InMemorySlidingWindowRateLimitStore(),
)
_GOOGLE_RATE_LIMITER = StoredSlidingWindowRateLimiter(
    policy=RateLimitPolicy(window_sec=300, max_requests=10),
    store=InMemorySlidingWindowRateLimitStore(),
)


@dataclass(frozen=True)
class AccountSession:
    user_id: str
    email: str
    display_name: str
    provider: AccountProvider
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class AccountLoginAttemptDecision:
    allowed: bool
    retry_after: int = 0


def account_auth_enabled(settings: Settings) -> bool:
    return settings.account_auth_enabled


def account_session_cookie_name() -> str:
    return _ACCOUNT_COOKIE_NAME


def issue_account_session(
    *,
    user: AccountUser,
    provider: AccountProvider,
    settings: Settings,
    now: datetime | None = None,
) -> AccountSession:
    current = _coerce_utc(now)
    return AccountSession(
        user_id=user.id,
        email=normalize_account_email(user.email),
        display_name=user.display_name,
        provider=provider,
        issued_at=current.isoformat(),
        expires_at=(
            current + timedelta(seconds=settings.account_session_ttl_sec)
        ).isoformat(),
    )


def build_account_authorization_context(
    session: AccountSession,
) -> AuthorizationContext:
    auth_mode = _AUTH_MODE_GOOGLE if session.provider == "google" else _AUTH_MODE_LOCAL
    user_owner_id = f"user:{session.user_id}"
    return AuthorizationContext(
        principal_id=PrincipalId(f"principal:user:{session.user_id}"),
        tenant_id=TenantId(_DEFAULT_TENANT_ID),
        scopes=FULL_SCOPES,
        credential_id=f"credential:account:{session.user_id}",
        legacy_owner_id=user_owner_id,
        auth_mode=auth_mode,
    )


def set_account_session_cookie(
    response: Response,
    *,
    session: AccountSession,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=_ACCOUNT_COOKIE_NAME,
        value=encode_account_session(session=session, settings=settings),
        max_age=settings.account_session_ttl_sec,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_account_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_ACCOUNT_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def read_account_session_from_request(
    request: Request,
    *,
    settings: Settings,
    now: datetime | None = None,
) -> AccountSession | None:
    raw = (request.cookies.get(_ACCOUNT_COOKIE_NAME) or "").strip()
    if not raw or not account_auth_enabled(settings):
        return None
    return decode_account_session(raw, settings=settings, now=now)


def encode_account_session(*, session: AccountSession, settings: Settings) -> str:
    payload = {
        "user_id": session.user_id,
        "email": session.email,
        "display_name": session.display_name,
        "provider": session.provider,
        "issued_at": session.issued_at,
        "expires_at": session.expires_at,
    }
    return _account_serializer(settings).dumps(payload)


def decode_account_session(
    raw: str,
    *,
    settings: Settings,
    now: datetime | None = None,
) -> AccountSession | None:
    try:
        payload = _account_serializer(settings).loads(
            raw,
            max_age=settings.account_session_ttl_sec,
        )
    except BadData:
        return None
    if not isinstance(payload, dict):
        return None
    user_id = str(payload.get("user_id", "")).strip()
    email = normalize_account_email(str(payload.get("email", "")))
    display_name = str(payload.get("display_name", "")).strip()
    provider = str(payload.get("provider", "")).strip()
    issued_at = str(payload.get("issued_at", "")).strip()
    expires_at = str(payload.get("expires_at", "")).strip()
    if provider not in {"local", "google"}:
        return None
    if not user_id or not email or not display_name or not issued_at or not expires_at:
        return None
    issued_dt = _parse_utc_timestamp(issued_at)
    expires_dt = _parse_utc_timestamp(expires_at)
    current = _coerce_utc(now)
    if (
        issued_dt is None
        or expires_dt is None
        or expires_dt <= issued_dt
        or expires_dt <= current
    ):
        return None
    return AccountSession(
        user_id=user_id,
        email=email,
        display_name=display_name,
        provider=provider,  # type: ignore[arg-type]
        issued_at=issued_dt.isoformat(),
        expires_at=expires_dt.isoformat(),
    )


def authenticate_local_account(
    repository: AccountRepository,
    *,
    email: str,
    password: str,
) -> AccountUser | None:
    normalized_email = normalize_account_email(email)
    user = repository.get_user_by_email(normalized_email)
    if user is None or not user.password_hash.strip():
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def resolve_google_account(
    repository: AccountRepository,
    *,
    provider_subject: str,
    email: str,
    display_name: str,
    now: datetime | None = None,
) -> AccountUser:
    current = _coerce_utc(now).isoformat()
    linked = repository.get_user_by_identity(
        provider="google",
        provider_subject=provider_subject,
    )
    if linked is not None:
        if linked.primary_provider == "google" and linked.display_name != display_name:
            repository.update_user(
                user_id=linked.id,
                display_name=display_name,
                primary_provider=linked.primary_provider,
                password_hash=linked.password_hash,
                updated_at=current,
            )
            return AccountUser(
                id=linked.id,
                email=linked.email,
                password_hash=linked.password_hash,
                display_name=display_name,
                primary_provider=linked.primary_provider,
                created_at=linked.created_at,
                updated_at=current,
            )
        return linked

    normalized_email = normalize_account_email(email)
    user = repository.get_user_by_email(normalized_email)
    if user is None:
        user = AccountUser(
            id=secrets.token_urlsafe(18),
            email=normalized_email,
            password_hash="",
            display_name=display_name,
            primary_provider="google",
            created_at=current,
            updated_at=current,
        )
        repository.create_user(user)
    elif not user.display_name.strip():
        repository.update_user(
            user_id=user.id,
            display_name=display_name,
            primary_provider=user.primary_provider,
            password_hash=user.password_hash,
            updated_at=current,
        )
        user = AccountUser(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            display_name=display_name,
            primary_provider=user.primary_provider,
            created_at=user.created_at,
            updated_at=current,
        )

    if (
        repository.get_identity(provider="google", provider_subject=provider_subject)
        is None
    ):
        repository.create_identity(
            AccountUserIdentity(
                id=secrets.token_urlsafe(18),
                user_id=user.id,
                provider="google",
                provider_subject=provider_subject,
                email=normalized_email,
                created_at=current,
                updated_at=current,
            )
        )
    return user


def evaluate_account_login_attempt(
    request: Request,
    *,
    route_group: str,
    email: str = "",
) -> AccountLoginAttemptDecision:
    subject = {
        "route_group": route_group,
        "client": _request_client_identity(request),
        "email": normalize_account_email(email),
    }
    limiter = (
        _GOOGLE_RATE_LIMITER if route_group.endswith("/google") else _LOGIN_RATE_LIMITER
    )
    decision = limiter.evaluate(subject=subject, now=_monotonic())
    return AccountLoginAttemptDecision(
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


def _account_serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        secret_key=settings.browser_session_secret,
        salt=_COOKIE_SERIALIZER_SALT,
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


def _monotonic() -> float:
    import time

    return time.monotonic()
