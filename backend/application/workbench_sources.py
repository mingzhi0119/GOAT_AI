"""Workbench source inventory entrypoints."""

from __future__ import annotations

from backend.application.exceptions import WorkbenchPermissionDeniedError
from backend.application.ports import Settings
from backend.application.workbench_shared import (
    ensure_agent_workbench_enabled,
    to_source_payload,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.workbench import WorkbenchSourcesResponse
from backend.services.authorizer import workbench_read_policy_allowed
from backend.services.workbench_source_registry import list_workbench_sources


def get_workbench_sources(
    *,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> WorkbenchSourcesResponse:
    """Return the visible retrieval-source registry for workbench tasks."""
    ensure_agent_workbench_enabled(settings)
    if not workbench_read_policy_allowed(auth_context):
        raise WorkbenchPermissionDeniedError(
            "Caller lacks the scopes required to read workbench sources."
        )
    return WorkbenchSourcesResponse(
        sources=[
            to_source_payload(source)
            for source in list_workbench_sources(
                settings=settings,
                auth_context=auth_context,
                request_id=request_id,
            )
        ]
    )
