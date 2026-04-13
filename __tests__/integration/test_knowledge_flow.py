"""Phase 15.10 — Knowledge pipeline integration tests.

Exercises the upload → ingest → search round-trip through the full
FastAPI TestClient stack. No live Ollama required; all assertions are
against the HTTP API contract documented in docs/api/openapi.json.
"""

from __future__ import annotations

import io
import pytest

pytestmark = pytest.mark.integration


class _KnowledgeAnswerFakeLLM:
    def __init__(self) -> None:
        self.last_prompt = ""

    def list_model_names(self) -> list[str]:
        return ["test-model"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return ["completion"], None

    def get_model_capabilities(self, model: str) -> list[str]:
        return self.describe_model_for_api(model)[0]

    def get_model_context_length(self, model: str) -> int | None:
        return self.describe_model_for_api(model)[1]

    def supports_tool_calling(self, model: str) -> bool:
        return False

    def stream_tokens(self, *args: object, **kwargs: object):
        if False:
            yield ""

    def stream_tokens_with_tools(self, *args: object, **kwargs: object):
        if False:
            yield ""

    def plan_tool_call(self, *args: object, **kwargs: object):
        return None

    def stream_tool_followup(self, *args: object, **kwargs: object):
        if False:
            yield ""

    def generate_completion(self, model: str, prompt: str, **_: object) -> str:
        self.last_prompt = prompt
        if "Retrieved knowledge context:" in prompt:
            return "Risk management reduces operational uncertainty."
        return (
            "I could not find evidence in the indexed knowledge base for that question."
        )


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
    upload = _upload(
        app_client, b"Strategic planning improves organizational outcomes."
    )
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


def test_answers_returns_synthesized_answer_with_citations(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.platform.dependencies import get_llm_client

    assert isinstance(app_client, TestClient)
    fake_llm = _KnowledgeAnswerFakeLLM()
    app_client.app.dependency_overrides[get_llm_client] = lambda: fake_llm
    upload = _upload(app_client, b"Risk management reduces operational uncertainty.")
    doc_id = upload["document_id"]
    _ingest(app_client, doc_id)
    try:
        resp = app_client.post(
            "/api/knowledge/answers",
            json={
                "query": "risk management",
                "document_ids": [doc_id],
                "top_k": 3,
            },
        )
    finally:
        app_client.app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Risk management reduces operational uncertainty."
    assert isinstance(body["citations"], list)
    assert len(body["citations"]) >= 1
    assert not body["answer"].startswith("Relevant retrieved context:")
    assert "synthesize rather than dumping snippets" in fake_llm.last_prompt
