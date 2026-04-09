from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from backend.domain.authorization import PrincipalId, Scope, TenantId


@dataclass(frozen=True)
class AuthorizationContext:
    principal_id: PrincipalId
    tenant_id: TenantId
    scopes: FrozenSet[Scope]
    credential_id: str
    legacy_owner_id: str
    auth_mode: str


@dataclass(frozen=True)
class CurrentAuthorizationContext:
    value: AuthorizationContext
