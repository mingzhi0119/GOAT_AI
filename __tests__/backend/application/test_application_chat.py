from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.application.chat import (
    _build_idempotency_context,
    _capture_idempotent_stream,
    prepare_chat_request,
)
from backend.application.exceptions import (
    ChatKnowledgeImageConflictError,
    ChatOwnerRequiredError,
    VisionNotSupported,
)
from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.models.chat import ChatMessage, ChatRequest
from backend.services import log_service
from goat_ai.config.settings import Settings


class _FakeLLM:
    def __init__(self, *, capabilities: list[str] | None = None) -> None:
        self._capabilities = capabilities or ["completion"]

    def get_model_capabilities(self, model: str) -> list[str]:
        _ = model
        return list(self._capabilities)


class _FakeIdempotencyStore:
    def claim(self, *, key: str, route: str, scope: str, request_hash: str):
        raise AssertionError("claim should not be called in this test")

    def store_completed(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
        status_code: int,
        content_type: str,
        body: str,
    ) -> None:
        raise AssertionError("store_completed should not be called in this test")

    def release_pending(
        self, *, key: str, route: str, scope: str, request_hash: str
    ) -> None:
        raise AssertionError("release_pending should not be called in this test")


def _auth_context(
    *,
    owner_id: str = "owner-1",
    tenant_id: str = "tenant-1",
    principal_id: str = "principal-1",
) -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId(principal_id),
        tenant_id=TenantId(tenant_id),
        scopes=frozenset({"chat:write", "media:read"}),
        credential_id="cred-1",
        legacy_owner_id=owner_id,
        auth_mode="api_key",
    )


class ApplicationChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            data_dir=root / "data",
        )
        log_service.init_db(self.settings.log_db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_prepare_chat_request_merges_images_and_builds_ollama_options(self) -> None:
        req = ChatRequest(
            model="vision-model",
            messages=[
                ChatMessage(role="assistant", content="Ack"),
                ChatMessage(role="user", content="Describe this image"),
            ],
            image_attachment_ids=["att-1", "att-2"],
            temperature=0.7,
            max_tokens=256,
            top_p=0.9,
            think="medium",
            plan_mode=True,
        )

        with patch(
            "backend.application.chat.load_images_base64_for_chat",
            return_value=["YmFzZTY0"],
        ) as load_images:
            prepared = prepare_chat_request(
                req=req,
                settings=self.settings,
                llm=_FakeLLM(capabilities=["completion", "vision"]),
                auth_context=_auth_context(),
                request_id="req-1",
            )

        load_images.assert_called_once()
        self.assertEqual(
            ["att-1", "att-2"], prepared.merged_messages[-1].image_attachment_ids
        )
        self.assertEqual(["YmFzZTY0"], prepared.vision_last_user_images_base64)
        self.assertEqual(
            {
                "temperature": 0.7,
                "num_predict": 256,
                "top_p": 0.9,
                "think": "medium",
            },
            prepared.ollama_options,
        )
        self.assertTrue(prepared.plan_mode)

    def test_prepare_chat_request_rejects_mixed_knowledge_and_image_inputs(
        self,
    ) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
            knowledge_document_ids=["doc-1"],
            image_attachment_ids=["att-1"],
        )

        with self.assertRaises(ChatKnowledgeImageConflictError):
            prepare_chat_request(
                req=req,
                settings=self.settings,
                llm=_FakeLLM(),
                auth_context=_auth_context(),
            )

    def test_prepare_chat_request_requires_owner_when_enabled(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        with self.assertRaises(ChatOwnerRequiredError):
            prepare_chat_request(
                req=req,
                settings=replace(self.settings, require_session_owner=True),
                llm=_FakeLLM(),
                auth_context=_auth_context(owner_id=""),
            )

    def test_prepare_chat_request_rejects_non_vision_model(self) -> None:
        req = ChatRequest(
            model="text-only-model",
            messages=[ChatMessage(role="user", content="Describe this image")],
            image_attachment_ids=["att-1"],
        )

        with patch(
            "backend.application.chat.load_images_base64_for_chat",
            return_value=["YmFzZTY0"],
        ):
            with self.assertRaises(VisionNotSupported):
                prepare_chat_request(
                    req=req,
                    settings=self.settings,
                    llm=_FakeLLM(capabilities=["completion"]),
                    auth_context=_auth_context(),
                )

    def test_capture_idempotent_stream_stores_completed_body_for_replay(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
            session_id="sess-1",
        )
        context = _build_idempotency_context(
            req=req,
            user_name="Simon",
            settings=self.settings,
            idempotency_key="idem-1",
        )

        self.assertIsNotNone(context)
        assert context is not None

        claim = context.store.claim(
            key=context.key,
            route=context.route,
            scope=context.scope,
            request_hash=context.request_hash,
        )
        self.assertEqual("claimed", claim.state)

        def source_stream() -> list[str]:
            return [
                'data: {"type": "token", "token": "Hello"}\n\n',
                'data: {"type": "done"}\n\n',
            ]

        captured = list(
            _capture_idempotent_stream(iter(source_stream()), context=context)
        )

        self.assertEqual(source_stream(), captured)
        replay = context.store.claim(
            key=context.key,
            route=context.route,
            scope=context.scope,
            request_hash=context.request_hash,
        )
        self.assertEqual("replay", replay.state)
        self.assertEqual("".join(source_stream()), replay.completed.body)

    def test_build_idempotency_context_uses_injected_store_factory(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
            session_id="sess-2",
        )
        fake_store = _FakeIdempotencyStore()

        context = _build_idempotency_context(
            req=req,
            user_name="Simon",
            settings=self.settings,
            idempotency_key="idem-injected",
            idempotency_store_factory=lambda _: fake_store,
        )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertIs(context.store, fake_store)


if __name__ == "__main__":
    unittest.main()
