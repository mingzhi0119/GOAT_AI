"""Phase 15.10 - retrieval-backed chat integration contract."""

from __future__ import annotations

import io

import pytest

pytestmark = pytest.mark.integration


class _KnowledgeAwareFakeLLM:
    def __init__(self) -> None:
        self.last_system_prompt = ""

    def list_model_names(self) -> list[str]:
        return ["test-model"]

    def get_model_capabilities(self, model: str) -> list[str]:
        return ["completion"]

    def supports_tool_calling(self, model: str) -> bool:
        return False

    def stream_tokens(
        self,
        model: str,
        messages: list[dict[str, object]],
        system_prompt: str,
        **_: object,
    ):
        self.last_system_prompt = system_prompt
        yield "Synthesized "
        yield "answer"

    def stream_tokens_with_tools(self, *args: object, **kwargs: object):
        if False:
            yield ""

    def plan_tool_call(self, *args: object, **kwargs: object):
        return None

    def stream_tool_followup(self, *args: object, **kwargs: object):
        if False:
            yield ""

    def generate_completion(self, model: str, prompt: str, **_: object) -> str:
        return "Knowledge chat title"


def _upload_and_ingest(client: object) -> str:
    from fastapi.testclient import TestClient

    assert isinstance(client, TestClient)
    upload = client.post(
        "/api/knowledge/uploads",
        files={
            "file": (
                "strategy.txt",
                io.BytesIO(
                    b"Porter Five Forces explains competitive pressure and buyer power."
                ),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 200, upload.text
    document_id = upload.json()["document_id"]
    ingest = client.post(
        "/api/knowledge/ingestions",
        json={"document_id": document_id},
    )
    assert ingest.status_code == 200, ingest.text
    return document_id


def test_chat_with_knowledge_injects_context_and_persists_documents(
    app_client: object,
) -> None:
    from fastapi.testclient import TestClient

    from backend.dependencies import get_llm_client, get_title_generator

    assert isinstance(app_client, TestClient)
    fake_llm = _KnowledgeAwareFakeLLM()
    app_client.app.dependency_overrides[get_llm_client] = lambda: fake_llm
    app_client.app.dependency_overrides[get_title_generator] = lambda: fake_llm
    try:
        document_id = _upload_and_ingest(app_client)
        response = app_client.post(
            "/api/chat",
            json={
                "model": "test-model",
                "session_id": "rag-integration-1",
                "knowledge_document_ids": [document_id],
                "messages": [
                    {
                        "role": "user",
                        "content": "What does the indexed strategy note say?",
                    }
                ],
            },
        )
    finally:
        app_client.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert "Synthesized " in response.text
    assert "answer" in response.text
    assert "Retrieved knowledge context:" in fake_llm.last_system_prompt
    assert "synthesize rather than dumping snippets" in fake_llm.last_system_prompt
    assert "competitive pressure" in fake_llm.last_system_prompt

    history = app_client.get("/api/history/rag-integration-1")
    assert history.status_code == 200, history.text
    body = history.json()
    assert body["knowledge_documents"] == [
        {
            "document_id": document_id,
            "filename": "strategy.txt",
            "mime_type": "text/plain",
        }
    ]
