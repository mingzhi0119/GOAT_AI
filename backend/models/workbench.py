"""Pydantic schemas for future agent/workbench task orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

WorkbenchTaskKind = Literal["plan", "browse", "deep_research", "canvas"]


class WorkbenchTaskRequest(BaseModel):
    """Scaffold request body for future long-running workbench tasks."""

    task_kind: WorkbenchTaskKind = Field(
        description="Planned task surface requested by the client."
    )
    prompt: str = Field(min_length=1, description="Primary user instruction.")
    session_id: str | None = Field(
        default=None,
        description="Optional chat/session affinity for future task replay.",
    )
    project_id: str | None = Field(
        default=None,
        description="Optional project/memory scope for future project workspaces.",
    )
    knowledge_document_ids: list[str] = Field(
        default_factory=list,
        description="Optional attached knowledge documents for retrieval-aware tasks.",
    )
    connector_ids: list[str] = Field(
        default_factory=list,
        description="Optional connector scopes for future browse/research tasks.",
    )
