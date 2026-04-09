"""Persist generated chat artifacts and derive downloadable files from assistant text."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from docx import Document as DocxDocument
from openpyxl import Workbook
from openpyxl.styles import Alignment

from backend.models.artifact import ChatArtifact
from backend.services.exceptions import ArtifactNotFound
from backend.types import Settings

_ARTIFACT_LINK_RE = re.compile(
    r"\[([^\]]+)\]\(([^)\s]+\.(?:md|txt|csv|xlsx|docx))\)",
    re.IGNORECASE,
)
_SUPPORTED_EXTENSIONS = {"md", "txt", "csv", "xlsx", "docx"}


@dataclass(frozen=True)
class PersistedArtifactRecord:
    id: str
    session_id: str
    owner_id: str
    filename: str
    mime_type: str
    byte_size: int
    storage_path: str
    source_message_index: int
    created_at: str
    tenant_id: str = "tenant:default"
    principal_id: str = ""


@dataclass(frozen=True)
class PreparedArtifact:
    filename: str
    mime_type: str
    content: bytes
    label: str | None = None


def artifact_to_wire(record: PersistedArtifactRecord) -> ChatArtifact:
    """Convert a stored artifact record to the typed API payload."""
    return ChatArtifact(
        artifact_id=record.id,
        filename=record.filename,
        mime_type=record.mime_type,
        byte_size=record.byte_size,
        download_url=f"/api/artifacts/{record.id}",
        label=record.filename,
    )


def create_chat_artifacts_from_text(
    *,
    assistant_text: str,
    settings: Settings,
    session_id: str | None,
    owner_id: str,
    tenant_id: str = "tenant:default",
    principal_id: str = "",
    source_message_index: int,
    register_artifact: Callable[[PersistedArtifactRecord], None],
) -> list[ChatArtifact]:
    """Derive downloadable artifacts from assistant output and persist them."""
    prepared = _extract_artifact_candidates(assistant_text=assistant_text)
    out: list[ChatArtifact] = []
    for item in prepared:
        record = persist_artifact(
            prepared=item,
            settings=settings,
            session_id=session_id or "",
            owner_id=owner_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            source_message_index=source_message_index,
            register_artifact=register_artifact,
        )
        out.append(artifact_to_wire(record))
    return out


def persist_artifact(
    *,
    prepared: PreparedArtifact,
    settings: Settings,
    session_id: str,
    owner_id: str,
    tenant_id: str,
    principal_id: str,
    source_message_index: int,
    register_artifact: Callable[[PersistedArtifactRecord], None],
) -> PersistedArtifactRecord:
    """Persist one artifact file and register it via the caller-supplied repository hook."""
    artifact_id = f"art-{uuid4().hex}"
    base = settings.data_dir / "uploads" / "artifacts" / artifact_id
    base.mkdir(parents=True, exist_ok=True)
    target = base / prepared.filename
    target.write_bytes(prepared.content)
    record = PersistedArtifactRecord(
        id=artifact_id,
        session_id=session_id,
        owner_id=owner_id,
        filename=prepared.filename,
        mime_type=prepared.mime_type,
        byte_size=len(prepared.content),
        storage_path=str(target),
        source_message_index=source_message_index,
        created_at=_now_iso(),
        tenant_id=tenant_id,
        principal_id=principal_id,
    )
    register_artifact(record)
    return record


def load_artifact_for_download(
    *,
    artifact_id: str,
    settings: Settings,
    request_owner: str,
    get_artifact: Callable[[str], PersistedArtifactRecord | None],
) -> PersistedArtifactRecord:
    """Resolve one artifact, enforcing owner scoping when configured."""
    record = get_artifact(artifact_id)
    if record is None:
        raise ArtifactNotFound("Chat artifact not found.")
    if settings.require_session_owner and record.owner_id != request_owner:
        raise ArtifactNotFound("Chat artifact not found.")
    if (
        settings.require_session_owner is False
        and request_owner
        and record.owner_id
        and record.owner_id != request_owner
    ):
        raise ArtifactNotFound("Chat artifact not found.")
    if not Path(record.storage_path).is_file():
        raise ArtifactNotFound("Chat artifact not found.")
    return record


def _extract_artifact_candidates(*, assistant_text: str) -> list[PreparedArtifact]:
    seen: set[str] = set()
    out: list[PreparedArtifact] = []
    for match in _ARTIFACT_LINK_RE.finditer(assistant_text):
        filename = Path(match.group(2)).name.strip()
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in _SUPPORTED_EXTENSIONS or filename.lower() in seen:
            continue
        prepared = _build_prepared_artifact(
            filename=filename, assistant_text=assistant_text
        )
        if prepared is None:
            continue
        out.append(prepared)
        seen.add(filename.lower())
    return out


def _build_prepared_artifact(
    *, filename: str, assistant_text: str
) -> PreparedArtifact | None:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "md":
        body = assistant_text.encode("utf-8")
        return PreparedArtifact(
            filename=filename, mime_type="text/markdown", content=body
        )
    if ext == "txt":
        body = _markdown_to_plain_text(assistant_text).encode("utf-8")
        return PreparedArtifact(filename=filename, mime_type="text/plain", content=body)
    if ext == "csv":
        return _prepared_csv(filename=filename, assistant_text=assistant_text)
    if ext == "xlsx":
        return _prepared_xlsx(filename=filename, assistant_text=assistant_text)
    if ext == "docx":
        return _prepared_docx(filename=filename, assistant_text=assistant_text)
    return None


def _prepared_csv(*, filename: str, assistant_text: str) -> PreparedArtifact:
    rows = _extract_markdown_table_rows(assistant_text)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow(["content"])
        for line in _markdown_to_plain_text(assistant_text).splitlines():
            if line.strip():
                writer.writerow([line.strip()])
    return PreparedArtifact(
        filename=filename,
        mime_type="text/csv",
        content=buffer.getvalue().encode("utf-8"),
    )


def _prepared_xlsx(*, filename: str, assistant_text: str) -> PreparedArtifact:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Generated"
    rows = _extract_markdown_table_rows(assistant_text)
    if rows:
        for r_index, row in enumerate(rows, start=1):
            for c_index, value in enumerate(row, start=1):
                cell = sheet.cell(row=r_index, column=c_index, value=value)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    else:
        plain = _markdown_to_plain_text(assistant_text).strip() or "Generated file"
        sheet["A1"] = plain
        sheet["A1"].alignment = Alignment(wrap_text=True, vertical="top")
        sheet.column_dimensions["A"].width = 80
    output = io.BytesIO()
    workbook.save(output)
    return PreparedArtifact(
        filename=filename,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=output.getvalue(),
    )


def _prepared_docx(*, filename: str, assistant_text: str) -> PreparedArtifact:
    document = DocxDocument()
    for line in _markdown_to_plain_text(assistant_text).splitlines():
        if line.strip():
            document.add_paragraph(line.strip())
    output = io.BytesIO()
    document.save(output)
    return PreparedArtifact(
        filename=filename,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=output.getvalue(),
    )


def _extract_markdown_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.count("|") < 2:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _markdown_to_plain_text(text: str) -> str:
    plain = _ARTIFACT_LINK_RE.sub(
        lambda match: f"{match.group(1)} ({Path(match.group(2)).name})", text
    )
    plain = re.sub(r"`{1,3}", "", plain)
    return plain.strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
