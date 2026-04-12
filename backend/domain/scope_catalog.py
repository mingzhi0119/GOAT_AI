from __future__ import annotations

from backend.domain.authorization import Scope

WORKBENCH_READ_SCOPE: Scope = "workbench:read"
WORKBENCH_WRITE_SCOPE: Scope = "workbench:write"
WORKBENCH_EXPORT_SCOPE: Scope = "workbench:export"

READ_SCOPES: frozenset[Scope] = frozenset(
    {
        "chat:read",
        "history:read",
        "knowledge:read",
        "media:read",
        "artifact:read",
        WORKBENCH_READ_SCOPE,
    }
)

WRITE_SCOPES: frozenset[Scope] = frozenset(
    {
        "chat:write",
        "history:write",
        "knowledge:write",
        "media:write",
        "artifact:write",
        "sandbox:execute",
        WORKBENCH_WRITE_SCOPE,
        WORKBENCH_EXPORT_SCOPE,
    }
)

FULL_SCOPES: frozenset[Scope] = frozenset({*READ_SCOPES, *WRITE_SCOPES})
