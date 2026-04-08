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

from backend.services.knowledge_storage import knowledge_document_dir, knowledge_vector_dir
from goat_ai.config import Settings

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


def normalize_document(*, settings: Settings, document_id: str, filename: str) -> str:
    source_path = _source_path(settings=settings, document_id=document_id, filename=filename)
    ext = source_path.suffix.lower()
    if ext == ".csv":
        dataframe = pd.read_csv(source_path)
        return _dataframe_to_text(dataframe)
    if ext == ".xlsx":
        dataframe = pd.read_excel(source_path)
        return _dataframe_to_text(dataframe)
    if ext == ".pdf":
        return _pdf_to_text(source_path)
    if ext == ".docx":
        return _docx_to_text(source_path)
    return source_path.read_text(encoding="utf-8")


def persist_normalized_text(*, settings: Settings, document_id: str, text: str) -> Path:
    normalized_dir = knowledge_document_dir(settings, document_id) / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    output_path = normalized_dir / "extracted.txt"
    output_path.write_text(text, encoding="utf-8")
    metadata_path = normalized_dir / "metadata.json"
    metadata_path.write_text(json.dumps({"char_length": len(text)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


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
            chunks.append(KnowledgeChunk(chunk_index=len(chunks), text=current, char_start=start, char_end=end))
            cursor = end
            current = piece
            start = cursor
            continue
        if not current:
            start = cursor
        current = candidate
        cursor = start + len(current)

    if current:
        chunks.append(KnowledgeChunk(chunk_index=len(chunks), text=current, char_start=start, char_end=start + len(current)))
    return chunks


def persist_vector_index(
    *,
    settings: Settings,
    document_id: str,
    filename: str,
    chunks: list[KnowledgeChunk],
    backend_name: str,
) -> str:
    vector_dir = knowledge_vector_dir(settings, backend_name)
    vector_dir.mkdir(parents=True, exist_ok=True)
    output_path = vector_dir / f"{document_id}.json"
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
    output_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(output_path)


def search_vector_index(
    *,
    settings: Settings,
    backend_name: str,
    query: str,
    document_filters: list[str],
) -> list[KnowledgeSearchHit]:
    vector_dir = knowledge_vector_dir(settings, backend_name)
    if not vector_dir.is_dir():
        return []

    query_vector = _embed_text(query)
    hits: list[KnowledgeSearchHit] = []
    for path in vector_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        document_id = str(payload["document_id"])
        if document_filters and document_id not in document_filters:
            continue
        filename = str(payload["filename"])
        for chunk in payload.get("chunks", []):
            score = _cosine_similarity(query_vector, [float(value) for value in chunk.get("vector", [])])
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


def _source_path(*, settings: Settings, document_id: str, filename: str) -> Path:
    ext = filename.rsplit(".", 1)[-1].lower()
    return knowledge_document_dir(settings, document_id) / "original" / f"source.{ext}"


def _dataframe_to_text(dataframe: pd.DataFrame) -> str:
    csv_buffer = io.StringIO()
    dataframe.to_csv(csv_buffer, index=False)
    columns = ", ".join(str(column) for column in dataframe.columns)
    return f"Columns: {columns}\n\n{csv_buffer.getvalue().strip()}"


def _pdf_to_text(source_path: Path) -> str:
    reader = PdfReader(str(source_path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if not text.strip():
        raise ValueError("PDF extraction produced no text.")
    return text


def _docx_to_text(source_path: Path) -> str:
    document = DocxDocument(str(source_path))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
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
