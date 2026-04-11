from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.domain.authz_types import AuthorizationContext

DEFAULT_TENANT_ID = "tenant:default"


@dataclass(frozen=True, kw_only=True)
class PersistedResourceOwnership:
    """Explicit persisted-resource ownership envelope used at repository boundaries."""

    owner_id: str = ""
    tenant_id: str = DEFAULT_TENANT_ID
    principal_id: str = ""

    @classmethod
    def from_auth_context(cls, ctx: AuthorizationContext) -> PersistedResourceOwnership:
        return cls(
            owner_id=ctx.legacy_owner_id,
            tenant_id=ctx.tenant_id.value,
            principal_id=ctx.principal_id.value,
        )


class SupportsResourceOwnership(Protocol):
    @property
    def ownership(self) -> PersistedResourceOwnership: ...


def ownership_from_fields(
    *,
    owner_id: str = "",
    tenant_id: str = DEFAULT_TENANT_ID,
    principal_id: str = "",
) -> PersistedResourceOwnership:
    return PersistedResourceOwnership(
        owner_id=owner_id,
        tenant_id=tenant_id or DEFAULT_TENANT_ID,
        principal_id=principal_id,
    )


def ownership_from_resource(resource: object) -> PersistedResourceOwnership:
    ownership = getattr(resource, "ownership", None)
    if isinstance(ownership, PersistedResourceOwnership):
        return ownership
    return ownership_from_fields(
        owner_id=str(getattr(resource, "owner_id", "") or ""),
        tenant_id=str(getattr(resource, "tenant_id", DEFAULT_TENANT_ID) or ""),
        principal_id=str(getattr(resource, "principal_id", "") or ""),
    )
