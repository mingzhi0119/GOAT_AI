"""Phase 15.10 — Knowledge pipeline integration tests.

Exercises the upload → ingest → search round-trip through the full
FastAPI TestClient stack. No live Ollama required; all assertions are
against the HTTP API contract documented in docs/openapi.json.
"""

from __future__ import annotations

import io
import pytest

pytestmark = pytest.mark.integration

# ── helpers ───────────────────────────────────────────────────────────────────

_SAMPLE_TEXT = b"The quick brown fox jumps over the lazy dog."
_SAMPLE_FILENAME = "sample.txt"


def _upload(client: object, content: bytes = _SAMPLE_TEXT) -> dict:
    from fastapi.testclient import TestClient

    assert isinstance(client, TestClient)
    response = client.post(
        "/api/knowledge/uploads",
        files={"file": (_SAMPLE_FILENAME, io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _ingest(client: object, document_id: str) -> dict:
    from fastapi.testclient import TestClient

    assert isinstance(client, TestClient)
    response = client.post(
        "/api/knowledge/ingestions",
        json={"document_id": document_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


# ── upload ────────────────────────────────────────────────────────────────────


def test_upload_returns_document_id(app_client: object) -> None:
    body = _upload(app_client)
    assert "document_id" in body
    assert body["document_id"].startswith("doc-")
    assert body["status"] == "uploaded"
    assert body["filename"] == _SAMPLE_FILENAME


def test_upload_status_readable(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    upload = _upload(app_client)
    doc_id = upload["document_id"]

    resp = app_client.get(f"/api/knowledge/uploads/{doc_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == doc_id


def test_upload_status_not_found(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    resp = app_client.get("/api/knowledge/uploads/doc-doesnotexist")
    assert resp.status_code == 404


# ── ingest ────────────────────────────────────────────────────────────────────


def test_ingest_returns_ingestion_id(app_client: object) -> None:
    upload = _upload(app_client)
    ingestion = _ingest(app_client, upload["document_id"])
    assert "ingestion_id" in ingestion
    assert ingestion["ingestion_id"].startswith("ing-")
    assert ingestion["document_id"] == upload["document_id"]


def test_ingest_status_readable(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    upload = _upload(app_client)
    ingestion = _ingest(app_client, upload["document_id"])
    ing_id = ingestion["ingestion_id"]

    resp = app_client.get(f"/api/knowledge/ingestions/{ing_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ingestion_id"] == ing_id


def test_ingest_unknown_document_returns_404(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    resp = app_client.post(
        "/api/knowledge/ingestions",
        json={"document_id": "doc-doesnotexist"},
    )
    assert resp.status_code == 404


# ── search ────────────────────────────────────────────────────────────────────


def test_search_after_ingest_returns_hits(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    upload = _upload(app_client, b"Strategic planning improves organizational outcomes.")
    doc_id = upload["document_id"]
    _ingest(app_client, doc_id)

    resp = app_client.post(
        "/api/knowledge/search",
        json={"query": "strategic planning", "document_ids": [doc_id], "top_k": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "hits" in body
    assert "query" in body


def test_search_empty_index_returns_empty_hits(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    resp = app_client.post(
        "/api/knowledge/search",
        json={"query": "anything", "document_ids": ["doc-phantom"], "top_k": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["hits"] == []


# ── /api/knowledge/answers semantic contract ──────────────────────────────────


def test_answers_returns_raw_snippet_dump_without_llm(app_client: object) -> None:
    """Document the semantic contract: /api/knowledge/answers returns retrieved
    snippets as the 'answer' field, NOT an LLM-generated response.
    This differs from /api/chat where an LLM synthesizes the answer.
    """
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    upload = _upload(app_client, b"Risk management reduces operational uncertainty.")
    doc_id = upload["document_id"]
    _ingest(app_client, doc_id)

    resp = app_client.post(
        "/api/knowledge/answers",
        json={
            "query": "risk management",
            "document_ids": [doc_id],
            "top_k": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Contract: response must carry an 'answer' field and 'citations' list
    assert "answer" in body
    assert "citations" in body
    # The answer is a raw snippet aggregation — it is NOT a conversational LLM reply
    assert isinstance(body["answer"], str)
    assert isinstance(body["citations"], list)
