from __future__ import annotations

import tempfile
from pathlib import Path

from backend.application.upload import analyze_upload_json
from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.models.upload import UploadAnalysisResponse
from goat_ai.config.settings import Settings


class _FakeIdempotencyStore:
    def __init__(self) -> None:
        self.completed_calls = 0

    def claim(self, *, key: str, route: str, scope: str, request_hash: str):
        _ = key, route, scope, request_hash
        return type("ClaimResult", (), {"state": "claimed", "completed": None})()

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
        _ = key, route, scope, request_hash, status_code, content_type, body
        self.completed_calls += 1

    def release_pending(
        self, *, key: str, route: str, scope: str, request_hash: str
    ) -> None:
        raise AssertionError("release_pending should not be called in this test")


def _settings(root: Path) -> Settings:
    return Settings(
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


def _auth_context() -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal-1"),
        tenant_id=TenantId("tenant-1"),
        scopes=frozenset({"knowledge:write"}),
        credential_id="cred-1",
        legacy_owner_id="owner-1",
        auth_mode="api_key",
    )


def test_analyze_upload_json_uses_injected_store_factory_for_idempotency() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        settings = _settings(Path(tmp))
        fake_store = _FakeIdempotencyStore()

        response = analyze_upload_json(
            content=b"month,revenue\nJan,10\n",
            filename="data.csv",
            settings=settings,
            auth_context=_auth_context(),
            idempotency_key="upload-1",
            ingest_upload_fn=lambda **_: UploadAnalysisResponse(
                filename="data.csv",
                suffix_prompt="Inspect this CSV for trends.",
                document_id="doc-1",
                ingestion_id="ing-1",
                status="completed",
                retrieval_mode="knowledge_rag",
                template_prompt="Analyze the upload.",
                chart=None,
            ),
            idempotency_store_factory=lambda _: fake_store,
        )

        assert response.filename == "data.csv"
        assert fake_store.completed_calls == 1
