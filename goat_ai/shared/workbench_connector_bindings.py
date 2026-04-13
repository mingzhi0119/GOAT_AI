from __future__ import annotations

import json
from dataclasses import dataclass

_DEFAULT_CAPABILITIES = ("search", "citations")
_DEFAULT_TASK_KINDS = ("browse", "deep_research")
_ALLOWED_CAPABILITIES = frozenset({"search", "fetch", "citations"})
_ALLOWED_TASK_KINDS = frozenset({"browse", "deep_research"})


@dataclass(frozen=True)
class WorkbenchConnectorDocument:
    document_id: str
    title: str
    content: str
    snippet: str


@dataclass(frozen=True)
class WorkbenchConnectorBinding:
    source_id: str
    display_name: str
    description: str
    capabilities: tuple[str, ...]
    task_kinds: tuple[str, ...]
    documents: tuple[WorkbenchConnectorDocument, ...]
    tenant_ids: tuple[str, ...] = ()
    principal_ids: tuple[str, ...] = ()
    owner_ids: tuple[str, ...] = ()


def parse_workbench_connector_bindings_json(
    raw_json: str,
) -> tuple[WorkbenchConnectorBinding, ...]:
    text = raw_json.strip()
    if not text:
        return ()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON must be valid JSON"
        ) from exc
    if not isinstance(payload, list):
        raise ValueError("GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON must decode to a list")

    bindings: list[WorkbenchConnectorBinding] = []
    seen_source_ids: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON entries must be objects"
            )
        source_id = _required_string(
            item.get("source_id"),
            message=(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON source_id must not be empty"
            ),
        )
        if not source_id.startswith("connector:"):
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON source_id must start with connector:"
            )
        if source_id in seen_source_ids:
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON source_id values must be unique"
            )
        seen_source_ids.add(source_id)
        display_name = _required_string(
            item.get("display_name"),
            message=(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON display_name must not be empty"
            ),
        )
        description = str(item.get("description", "")).strip() or (
            "Read-only connector binding provisioned by the operator for bounded "
            "workbench retrieval."
        )
        capabilities = _parse_string_list(
            item.get("capabilities", list(_DEFAULT_CAPABILITIES)),
            field_name="GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON capabilities",
        )
        if not capabilities:
            capabilities = _DEFAULT_CAPABILITIES
        invalid_capabilities = sorted(
            capability
            for capability in capabilities
            if capability not in _ALLOWED_CAPABILITIES
        )
        if invalid_capabilities:
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON capabilities must be drawn from "
                "search, fetch, citations"
            )
        task_kinds = _parse_string_list(
            item.get("task_kinds", list(_DEFAULT_TASK_KINDS)),
            field_name="GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON task_kinds",
        )
        if not task_kinds:
            task_kinds = _DEFAULT_TASK_KINDS
        invalid_task_kinds = sorted(
            task_kind
            for task_kind in task_kinds
            if task_kind not in _ALLOWED_TASK_KINDS
        )
        if invalid_task_kinds:
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON task_kinds must be browse and/or deep_research"
            )
        documents = item.get("documents", [])
        if not isinstance(documents, list):
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON documents must be a list"
            )
        if not documents:
            raise ValueError(
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON documents must not be empty"
            )
        bindings.append(
            WorkbenchConnectorBinding(
                source_id=source_id,
                display_name=display_name,
                description=description,
                capabilities=tuple(dict.fromkeys(capabilities)),
                task_kinds=tuple(dict.fromkeys(task_kinds)),
                documents=tuple(_parse_document(document) for document in documents),
                tenant_ids=tuple(
                    dict.fromkeys(
                        _parse_string_list(
                            item.get("tenant_ids", []),
                            field_name=(
                                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON tenant_ids"
                            ),
                        )
                    )
                ),
                principal_ids=tuple(
                    dict.fromkeys(
                        _parse_string_list(
                            item.get("principal_ids", []),
                            field_name=(
                                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON principal_ids"
                            ),
                        )
                    )
                ),
                owner_ids=tuple(
                    dict.fromkeys(
                        _parse_string_list(
                            item.get("owner_ids", []),
                            field_name=(
                                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON owner_ids"
                            ),
                        )
                    )
                ),
            )
        )
    return tuple(bindings)


def _parse_document(item: object) -> WorkbenchConnectorDocument:
    if not isinstance(item, dict):
        raise ValueError(
            "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON documents entries must be objects"
        )
    document_id = _required_string(
        item.get("document_id"),
        message=(
            "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON document_id must not be empty"
        ),
    )
    title = _required_string(
        item.get("title"),
        message="GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON document title must not be empty",
    )
    content = _required_string(
        item.get("content"),
        message=(
            "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON document content must not be empty"
        ),
    )
    snippet = str(item.get("snippet", "")).strip() or content[:280].strip()
    return WorkbenchConnectorDocument(
        document_id=document_id,
        title=title,
        content=content,
        snippet=snippet,
    )


def _required_string(value: object, *, message: str) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError(message)
    return text


def _parse_string_list(value: object, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} entries must be strings")
        stripped = item.strip()
        if not stripped:
            raise ValueError(f"{field_name} entries must not be empty")
        items.append(stripped)
    return tuple(items)
