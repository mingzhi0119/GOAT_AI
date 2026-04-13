from __future__ import annotations

import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from docx import Document as DocxDocument
from pypdf import PdfReader

from backend.services.knowledge_storage import (
    knowledge_original_storage_key,
    knowledge_normalized_metadata_storage_key,
    knowledge_normalized_text_storage_key,
    knowledge_vector_storage_key,
    write_text_object,
)
from goat_ai.config.settings import Settings
from goat_ai.uploads import build_object_store, knowledge_vector_index_prefix

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_VECTOR_DIMS = 128


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_index: int
    text: str
    char_start: int
    char_end: int


@dataclass(frozen=True)
class KnowledgeSearchHit:
    chunk_id: str
    document_id: str
    filename: str
    snippet: str
    score: float


def normalize_document(
    *,
    settings: Settings,
    document_id: str,
    filename: str,
    storage_key: str | None = None,
    storage_path: str | None = None,
) -> str:
    source_bytes = _load_source_bytes(
        settings=settings,
        document_id=document_id,
        filename=filename,
        storage_key=storage_key,
        storage_path=storage_path,
    )
    ext = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
    if ext == ".csv":
        dataframe = pd.read_csv(io.BytesIO(source_bytes))
        return _dataframe_to_text(dataframe)
    if ext == ".xlsx":
        dataframe = pd.read_excel(io.BytesIO(source_bytes))
        return _dataframe_to_text(dataframe)
    if ext == ".pdf":
        return _pdf_to_text(source_bytes)
    if ext == ".docx":
        return _docx_to_text(source_bytes)
    return source_bytes.decode("utf-8")


def persist_normalized_text(*, settings: Settings, document_id: str, text: str) -> str:
    write_text_object(
        settings=settings,
        storage_key=knowledge_normalized_text_storage_key(document_id),
        text=text,
    )
    metadata_key = knowledge_normalized_metadata_storage_key(document_id)
    write_text_object(
        settings=settings,
        storage_key=metadata_key,
        text=json.dumps({"char_length": len(text)}, ensure_ascii=False, indent=2)
        + "\n",
    )
    return metadata_key


def chunk_text(text: str, *, max_chars: int = 800) -> list[KnowledgeChunk]:
    pieces = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[KnowledgeChunk] = []
    cursor = 0
    current = ""
    start = 0

    for piece in pieces or [text.strip()]:
        candidate = piece if not current else f"{current}\n\n{piece}"
        if current and len(candidate) > max_chars:
            end = start + len(current)
            chunks.append(
                KnowledgeChunk(
                    chunk_index=len(chunks),
                    text=current,
                    char_start=start,
                    char_end=end,
                )
            )
            cursor = end
            current = piece
            start = cursor
            continue
        if not current:
            start = cursor
        current = candidate
        cursor = start + len(current)

    if current:
        chunks.append(
            KnowledgeChunk(
                chunk_index=len(chunks),
                text=current,
                char_start=start,
                char_end=start + len(current),
            )
        )
    return chunks


def persist_vector_index(
    *,
    settings: Settings,
    document_id: str,
    filename: str,
    chunks: list[KnowledgeChunk],
    backend_name: str,
) -> str:
    output_key = knowledge_vector_storage_key(document_id, backend_name)
    payload = {
        "document_id": document_id,
        "filename": filename,
        "chunks": [
            {
                "chunk_index": chunk.chunk_index,
                "vector_ref": f"{document_id}:{chunk.chunk_index}",
                "vector": _embed_text(chunk.text),
                "snippet": chunk.text[:400],
            }
            for chunk in chunks
        ],
    }
    write_text_object(
        settings=settings,
        storage_key=output_key,
        text=json.dumps(payload, ensure_ascii=False) + "\n",
    )
    return output_key


def search_vector_index(
    *,
    settings: Settings,
    backend_name: str,
    query: str,
    document_filters: list[str],
) -> list[KnowledgeSearchHit]:
    query_vector = _embed_text(query)
    hits: list[KnowledgeSearchHit] = []
    payloads = _iter_vector_payloads(settings=settings, backend_name=backend_name)
    for payload in payloads:
        document_id = str(payload["document_id"])
        if document_filters and document_id not in document_filters:
            continue
        filename = str(payload["filename"])
        for chunk in payload.get("chunks", []):
            score = _cosine_similarity(
                query_vector, [float(value) for value in chunk.get("vector", [])]
            )
            if score <= 0:
                continue
            hits.append(
                KnowledgeSearchHit(
                    chunk_id=str(chunk["vector_ref"]),
                    document_id=document_id,
                    filename=filename,
                    snippet=str(chunk.get("snippet", "")),
                    score=score,
                )
            )
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits


def _load_source_bytes(
    *,
    settings: Settings,
    document_id: str,
    filename: str,
    storage_key: str | None,
    storage_path: str | None,
) -> bytes:
    if storage_key:
        return build_object_store(settings).read_bytes(storage_key)
    if document_id and "." in filename:
        inferred_key = knowledge_original_storage_key(
            document_id,
            filename.rsplit(".", 1)[-1].lower(),
        )
        store = build_object_store(settings)
        if store.exists(inferred_key):
            return store.read_bytes(inferred_key)
    if storage_path:
        path = Path(storage_path)
        if path.is_file():
            return path.read_bytes()
    ext = filename.rsplit(".", 1)[-1].lower()
    legacy_path = (
        settings.data_dir
        / "uploads"
        / "knowledge"
        / document_id
        / "original"
        / f"source.{ext}"
    )
    return legacy_path.read_bytes()


def _dataframe_to_text(dataframe: pd.DataFrame) -> str:
    csv_buffer = io.StringIO()
    dataframe.to_csv(csv_buffer, index=False)
    columns = ", ".join(str(column) for column in dataframe.columns)
    return f"Columns: {columns}\n\n{csv_buffer.getvalue().strip()}"


def _iter_vector_payloads(
    *, settings: Settings, backend_name: str
) -> list[dict[str, object]]:
    prefix = knowledge_vector_index_prefix(backend_name=backend_name)
    payloads: list[dict[str, object]] = []
    store = build_object_store(settings)
    for storage_key in store.list_keys(prefix=prefix):
        payloads.append(json.loads(store.read_text(storage_key)))
    legacy_vector_dir = settings.data_dir / "vector_index" / backend_name
    if (
        settings.object_store_backend != "local"
        or settings.object_store_root.resolve() != settings.data_dir.resolve()
    ) and legacy_vector_dir.is_dir():
        for path in legacy_vector_dir.glob("*.json"):
            payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def _pdf_to_text(source_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(source_bytes))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if not text.strip():
        raise ValueError("PDF extraction produced no text.")
    return text


def _docx_to_text(source_bytes: bytes) -> str:
    document = DocxDocument(io.BytesIO(source_bytes))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]
    text = "\n\n".join(paragraphs)
    if not text.strip():
        raise ValueError("DOCX extraction produced no text.")
    return text


def _embed_text(text: str) -> list[float]:
    vector = [0.0] * _VECTOR_DIMS
    for token in _TOKEN_RE.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % _VECTOR_DIMS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return float(sum(a * b for a, b in zip(left, right)))
