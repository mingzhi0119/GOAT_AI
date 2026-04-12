from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from backend.domain.authorization import PrincipalId, TenantId
from backend.domain.authz_types import AuthorizationContext
from backend.services.workbench_source_registry import (
    list_workbench_sources,
    normalize_requested_source_ids,
    resolve_requested_sources,
)
from goat_ai.config.settings import Settings


def _settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test system prompt",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        data_dir=root / "data",
        ready_skip_ollama_probe=True,
    )


def _auth_context(*, scopes: frozenset[str]) -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal:test"),
        tenant_id=TenantId("tenant:default"),
        scopes=scopes,  # type: ignore[arg-type]
        credential_id="cred-test",
        legacy_owner_id="",
        auth_mode="api_key",
    )


class WorkbenchSourceRegistryTests(unittest.TestCase):
    def test_normalize_requested_source_ids_dedupes_and_infers_knowledge(self) -> None:
        normalized = normalize_requested_source_ids(
            source_ids=[],
            connector_ids=["web", "web", "knowledge"],
            knowledge_document_ids=["doc-1"],
        )
        self.assertEqual(["web", "knowledge"], normalized)

        inferred = normalize_requested_source_ids(
            source_ids=[],
            connector_ids=[],
            knowledge_document_ids=["doc-1"],
        )
        self.assertEqual(["knowledge"], inferred)

    def test_list_sources_hides_knowledge_without_read_scope(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            sources = list_workbench_sources(
                settings=_settings(Path(tmp)),
                auth_context=_auth_context(scopes=frozenset({"workbench:read"})),
            )
        self.assertEqual(["web"], [source.source_id for source in sources])
        self.assertTrue(sources[0].runtime_ready)
        self.assertIsNone(sources[0].deny_reason)
        self.assertIn("DDGS", sources[0].description)

    def test_list_sources_marks_web_not_ready_when_provider_disabled(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(
                _settings(Path(tmp)),
                workbench_web_provider="disabled",
            )
            sources = list_workbench_sources(
                settings=settings,
                auth_context=_auth_context(scopes=frozenset({"workbench:read"})),
            )
        self.assertEqual(["web"], [source.source_id for source in sources])
        self.assertFalse(sources[0].runtime_ready)
        self.assertEqual("disabled_by_operator", sources[0].deny_reason)

    def test_resolve_requested_sources_rejects_denied_known_sources(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with self.assertRaisesRegex(PermissionError, "requested workbench sources"):
                resolve_requested_sources(
                    source_ids=["knowledge"],
                    settings=_settings(Path(tmp)),
                    auth_context=_auth_context(scopes=frozenset({"workbench:read"})),
                )

    def test_resolve_requested_sources_rejects_unknown_ids(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with self.assertRaisesRegex(ValueError, "Unknown or unavailable"):
                resolve_requested_sources(
                    source_ids=["unknown-source"],
                    settings=_settings(Path(tmp)),
                    auth_context=_auth_context(
                        scopes=frozenset({"workbench:read", "knowledge:read"})
                    ),
                )


if __name__ == "__main__":
    unittest.main()
