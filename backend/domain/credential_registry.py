from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import FrozenSet

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, Scope, TenantId
from goat_ai.config import Settings

_DEFAULT_TENANT = "tenant:default"
_AUTH_MODE_SHARED = "shared_key_v1"
_AUTH_MODE_REGISTRY = "credential_registry_v1"
_AUTH_MODE_LOCAL = "local_noauth_v1"

_READ_SCOPES: frozenset[Scope] = frozenset(
    {
        "chat:read",
        "history:read",
        "knowledge:read",
        "media:read",
        "artifact:read",
    }
)
_WRITE_SCOPES: frozenset[Scope] = frozenset(
    {
        "chat:write",
        "history:write",
        "knowledge:write",
        "media:write",
        "artifact:write",
        "sandbox:execute",
    }
)
_FULL_SCOPES: frozenset[Scope] = frozenset({*_READ_SCOPES, *_WRITE_SCOPES})


@dataclass(frozen=True)
class ApiCredential:
    credential_id: str
    secret_sha256: str
    principal_id: PrincipalId
    tenant_id: TenantId
    scopes: FrozenSet[Scope]
    status: str
    auth_mode: str
    description: str = ""


def _parse_scope_set(raw: object) -> frozenset[Scope]:
    if not isinstance(raw, list):
        raise ValueError("Credential scopes must be a JSON array.")
    scopes: set[Scope] = set()
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Credential scopes must be non-empty strings.")
        scopes.add(item.strip())  # type: ignore[arg-type]
    return frozenset(scopes)


def _build_default_credentials(settings: Settings) -> list[ApiCredential]:
    credentials: list[ApiCredential] = []
    if settings.api_key:
        credentials.append(
            ApiCredential(
                credential_id="credential:read-default",
                secret_sha256=_hash_secret(settings.api_key),
                principal_id=PrincipalId("principal:read-default"),
                tenant_id=TenantId(_DEFAULT_TENANT),
                scopes=_READ_SCOPES,
                status="active",
                auth_mode=_AUTH_MODE_SHARED,
                description="Derived from GOAT_API_KEY",
            )
        )
    if settings.api_key_write:
        credentials.append(
            ApiCredential(
                credential_id="credential:write-default",
                secret_sha256=_hash_secret(settings.api_key_write),
                principal_id=PrincipalId("principal:write-default"),
                tenant_id=TenantId(_DEFAULT_TENANT),
                scopes=_FULL_SCOPES,
                status="active",
                auth_mode=_AUTH_MODE_SHARED,
                description="Derived from GOAT_API_KEY_WRITE",
            )
        )
    return credentials


def load_api_credentials(settings: Settings) -> list[ApiCredential]:
    raw = settings.api_credentials_json.strip()
    if not raw:
        return _build_default_credentials(settings)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("GOAT_API_CREDENTIALS_JSON must be valid JSON.") from exc
    if not isinstance(payload, list):
        raise ValueError("GOAT_API_CREDENTIALS_JSON must be a JSON array.")

    credentials: list[ApiCredential] = []
    seen_ids: set[str] = set()
    seen_secret_hashes: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each credential entry must be an object.")
        credential_id = str(item.get("credential_id", "")).strip()
        secret_sha256 = _resolve_secret_hash(item)
        principal_id = str(item.get("principal_id", "")).strip()
        tenant_id = (
            str(item.get("tenant_id", _DEFAULT_TENANT)).strip() or _DEFAULT_TENANT
        )
        status = str(item.get("status", "active")).strip() or "active"
        auth_mode = _AUTH_MODE_REGISTRY
        if not credential_id or not secret_sha256 or not principal_id:
            raise ValueError(
                "Each credential requires credential_id, principal_id, and either secret or secret_sha256."
            )
        if credential_id in seen_ids:
            raise ValueError(f"Duplicate credential_id: {credential_id}")
        if secret_sha256 in seen_secret_hashes:
            raise ValueError("Duplicate credential secrets are not allowed.")
        if status not in {"active", "disabled"}:
            raise ValueError("Credential status must be 'active' or 'disabled'.")
        credentials.append(
            ApiCredential(
                credential_id=credential_id,
                secret_sha256=secret_sha256,
                principal_id=PrincipalId(principal_id),
                tenant_id=TenantId(tenant_id),
                scopes=_parse_scope_set(item.get("scopes", [])),
                status=status,
                auth_mode=auth_mode,
                description=str(item.get("description", "")),
            )
        )
        seen_ids.add(credential_id)
        seen_secret_hashes.add(secret_sha256)
    return credentials


def resolve_credential(
    *, provided_api_key: str, settings: Settings
) -> ApiCredential | None:
    provided_secret_hash = _hash_secret(provided_api_key)
    for credential in load_api_credentials(settings):
        if not hmac.compare_digest(credential.secret_sha256, provided_secret_hash):
            continue
        if credential.status != "active":
            return None
        return credential
    return None


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _resolve_secret_hash(item: dict[str, object]) -> str:
    secret_sha256 = str(item.get("secret_sha256", "")).strip().lower()
    raw_secret = str(item.get("secret", "")).strip()
    if secret_sha256:
        if len(secret_sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in secret_sha256
        ):
            raise ValueError(
                "Credential secret_sha256 must be a lowercase SHA-256 hex digest."
            )
        return secret_sha256
    if raw_secret:
        return _hash_secret(raw_secret)
    return ""


def build_local_authorization_context() -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal:local-noauth"),
        tenant_id=TenantId(_DEFAULT_TENANT),
        scopes=_FULL_SCOPES,
        credential_id="credential:local-noauth",
        legacy_owner_id="",
        auth_mode=_AUTH_MODE_LOCAL,
    )


def resolve_authorization_context(
    *,
    provided_api_key: str,
    settings: Settings,
    legacy_owner_id: str,
) -> AuthorizationContext | None:
    credential = resolve_credential(
        provided_api_key=provided_api_key,
        settings=settings,
    )
    if credential is None:
        return None
    return AuthorizationContext(
        principal_id=credential.principal_id,
        tenant_id=credential.tenant_id,
        scopes=credential.scopes,
        credential_id=credential.credential_id,
        legacy_owner_id=legacy_owner_id,
        auth_mode=credential.auth_mode,
    )
