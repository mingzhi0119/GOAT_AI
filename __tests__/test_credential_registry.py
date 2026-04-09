from __future__ import annotations

import unittest
from pathlib import Path

from backend.application.credential_registry import (
    load_api_credentials,
    resolve_authorization_context,
)
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


class CredentialRegistryTests(unittest.TestCase):
    def test_env_fallback_builds_default_credentials(self) -> None:
        settings = _settings(api_key="read-key", api_key_write="write-key")
        credentials = load_api_credentials(settings)
        self.assertEqual(2, len(credentials))
        self.assertEqual("principal:read-default", credentials[0].principal_id.value)
        self.assertIn("history:read", credentials[0].scopes)
        self.assertIn("history:write", credentials[1].scopes)

    def test_json_credentials_parse(self) -> None:
        settings = _settings(
            api_credentials_json="""
            [
              {
                "credential_id": "cred-1",
                "secret": "alpha",
                "principal_id": "principal:alpha",
                "tenant_id": "tenant:a",
                "status": "active",
                "scopes": ["history:read", "artifact:read"]
              }
            ]
            """,
        )
        credentials = load_api_credentials(settings)
        self.assertEqual("cred-1", credentials[0].credential_id)
        self.assertEqual("tenant:a", credentials[0].tenant_id.value)

    def test_disabled_credential_rejects_resolution(self) -> None:
        settings = _settings(
            api_credentials_json="""
            [
              {
                "credential_id": "cred-1",
                "secret": "alpha",
                "principal_id": "principal:alpha",
                "tenant_id": "tenant:a",
                "status": "disabled",
                "scopes": ["history:read"]
              }
            ]
            """,
        )
        ctx = resolve_authorization_context(
            provided_api_key="alpha",
            settings=settings,
            legacy_owner_id="alice",
        )
        self.assertIsNone(ctx)

    def test_duplicate_credential_rejected(self) -> None:
        settings = _settings(
            api_credentials_json="""
            [
              {
                "credential_id": "cred-1",
                "secret": "alpha",
                "principal_id": "principal:a",
                "status": "active",
                "scopes": ["history:read"]
              },
              {
                "credential_id": "cred-1",
                "secret": "beta",
                "principal_id": "principal:b",
                "status": "active",
                "scopes": ["history:read"]
              }
            ]
            """,
        )
        with self.assertRaises(ValueError):
            load_api_credentials(settings)
