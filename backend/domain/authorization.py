from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Scope = Literal[
    "chat:read",
    "chat:write",
    "history:read",
    "history:write",
    "knowledge:read",
    "knowledge:write",
    "media:read",
    "media:write",
    "artifact:read",
    "artifact:write",
    "sandbox:execute",
]


@dataclass(frozen=True)
class PrincipalId:
    value: str


@dataclass(frozen=True)
class TenantId:
    value: str


@dataclass(frozen=True)
class ResourceRef:
    resource_type: str
    resource_id: str


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str
    conceal_existence: bool = False
