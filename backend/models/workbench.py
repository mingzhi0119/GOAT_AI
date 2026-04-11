"""Pydantic schemas for durable workbench task orchestration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from backend.models.knowledge import KnowledgeCitation

WorkbenchTaskKind = Literal["plan", "browse", "deep_research", "canvas"]
WorkbenchTaskStatus = Literal["queued", "running", "completed", "failed"]
WorkbenchTaskEventType = Literal[
    "task.queued",
    "task.started",
    "retrieval.sources_resolved",
    "retrieval.step.completed",
    "retrieval.step.skipped",
    "task.completed",
    "task.failed",
]
WorkbenchSourceKind = Literal["builtin", "knowledge", "connector"]
WorkbenchSourceScopeKind = Literal["global", "knowledge_documents", "connector_binding"]


class WorkbenchTaskRequest(BaseModel):
    """Request body for durable long-running workbench tasks."""

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
    source_ids: list[str] = Field(
        default_factory=list,
        description="Optional retrieval source ids for browse, research, or plan context.",
    )
    connector_ids: list[str] = Field(
        default_factory=list,
        description="Deprecated alias for source_ids. Prefer source_ids for new clients.",
    )

    @model_validator(mode="after")
    def validate_source_inputs(self) -> "WorkbenchTaskRequest":
        if self.source_ids and self.connector_ids:
            raise ValueError("Provide either source_ids or connector_ids, not both.")
        return self


class WorkbenchTaskAcceptedResponse(BaseModel):
    """Minimal accepted-task payload returned when a workbench task is created."""

    task_id: str = Field(..., description="Stable durable task identifier.")
    task_kind: WorkbenchTaskKind = Field(
        ..., description="Task surface requested by the client."
    )
    status: WorkbenchTaskStatus = Field(
        ..., description="Current durable task lifecycle state."
    )
    created_at: str = Field(..., description="UTC ISO-8601 creation timestamp.")


class WorkbenchTaskStatusResponse(WorkbenchTaskAcceptedResponse):
    """Status payload returned when polling a durable workbench task."""

    updated_at: str = Field(..., description="UTC ISO-8601 last-update timestamp.")
    error_detail: str | None = Field(
        default=None,
        description="Optional stable human-readable failure detail.",
    )
    result: "WorkbenchTaskResultPayload | None" = Field(
        default=None,
        description=(
            "Optional completed task result. Current runtime guarantees markdown "
            "for plan tasks and may include citations for browse or deep_research "
            "tasks when retrieval succeeds."
        ),
    )


class WorkbenchTaskResultPayload(BaseModel):
    """Minimal inline result shape for a completed workbench task."""

    format: Literal["markdown"] = Field(
        default="markdown",
        description="Serialization format for the returned result content.",
    )
    content: str = Field(..., description="Rendered task result content.")
    citations: list[KnowledgeCitation] = Field(
        default_factory=list,
        description="Optional citations gathered during browse/research retrieval.",
    )


class WorkbenchTaskEventPayload(BaseModel):
    """One durable event emitted during task execution."""

    sequence: int = Field(..., description="Task-local event ordering number.")
    event_type: WorkbenchTaskEventType = Field(
        ..., description="Stable event name for this task lifecycle update."
    )
    created_at: str = Field(..., description="UTC ISO-8601 event timestamp.")
    status: WorkbenchTaskStatus | None = Field(
        default=None,
        description="Optional task lifecycle status associated with this event.",
    )
    message: str | None = Field(
        default=None,
        description="Optional stable human-readable event summary.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured metadata for clients that need richer polling.",
    )


class WorkbenchTaskEventsResponse(BaseModel):
    """Durable event timeline returned when polling workbench task progress."""

    task_id: str = Field(..., description="Stable durable task identifier.")
    events: list[WorkbenchTaskEventPayload] = Field(
        default_factory=list,
        description="Ordered durable events for this task.",
    )


class WorkbenchSourcePayload(BaseModel):
    """Declarative retrieval source entry for future workbench tasks."""

    source_id: str = Field(..., description="Stable source identifier used by tasks.")
    display_name: str = Field(..., description="Human-readable source label.")
    kind: WorkbenchSourceKind = Field(..., description="High-level source family.")
    scope_kind: WorkbenchSourceScopeKind = Field(
        ...,
        description="Whether the source is global, document-scoped, or connector-bound.",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Declared retrieval capabilities such as search, fetch, and citations.",
    )
    task_kinds: list[WorkbenchTaskKind] = Field(
        default_factory=list,
        description="Workbench task kinds that may eventually use this source.",
    )
    read_only: bool = Field(
        default=True,
        description="Whether the source is read-only from the model/runtime perspective.",
    )
    runtime_ready: bool = Field(
        ...,
        description="Whether the source can be used by the current backend runtime today.",
    )
    deny_reason: str | None = Field(
        default=None,
        description="Stable deny reason when the source exists but is not runtime-ready.",
    )
    description: str = Field(..., description="Concise operational description.")


class WorkbenchSourcesResponse(BaseModel):
    """Visible retrieval source inventory for the current caller."""

    sources: list[WorkbenchSourcePayload] = Field(
        default_factory=list,
        description="Sources the current caller can see for workbench retrieval tasks.",
    )
