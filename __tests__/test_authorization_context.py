from __future__ import annotations

import unittest
from pathlib import Path

from backend.domain.credential_registry import resolve_authorization_context
from goat_ai.config import Settings


def _settings(**overrides: object) -> Settings:
    base = dict(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=Path("."),
        logo_svg=Path("logo.svg"),
        log_db_path=Path("chat_logs.db"),
        data_dir=Path("data"),
        ready_skip_ollama_probe=True,
    )
    base.update(overrides)
    return Settings(**base)


class AuthorizationContextTests(unittest.TestCase):
    def test_api_key_resolves_to_context(self) -> None:
        settings = _settings(api_key="read-key", api_key_write="write-key")
        ctx = resolve_authorization_context(
            provided_api_key="read-key",
            settings=settings,
            legacy_owner_id="alice",
        )
        assert ctx is not None
        self.assertEqual("principal:read-default", ctx.principal_id.value)
        self.assertEqual("tenant:default", ctx.tenant_id.value)
        self.assertEqual("alice", ctx.legacy_owner_id)

    def test_write_key_includes_write_scopes(self) -> None:
        settings = _settings(api_key="read-key", api_key_write="write-key")
        ctx = resolve_authorization_context(
            provided_api_key="write-key",
            settings=settings,
            legacy_owner_id="",
        )
        assert ctx is not None
        self.assertIn("history:write", ctx.scopes)
        self.assertIn("artifact:write", ctx.scopes)

    def test_invalid_key_returns_none(self) -> None:
        settings = _settings(api_key="read-key")
        ctx = resolve_authorization_context(
            provided_api_key="wrong",
            settings=settings,
            legacy_owner_id="",
        )
        self.assertIsNone(ctx)
