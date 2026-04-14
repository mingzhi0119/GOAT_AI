from __future__ import annotations

import unittest
from pathlib import Path

from backend.domain.credential_registry import (
    build_local_authorization_context,
    load_api_credentials,
    resolve_authorization_context,
    resolve_credential,
)
from goat_ai.config.settings import Settings


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
    def test_build_local_authorization_context_preserves_owner_when_provided(
        self,
    ) -> None:
        ctx = build_local_authorization_context(legacy_owner_id="alice")

        self.assertEqual("alice", ctx.legacy_owner_id)
        self.assertEqual("principal:local-noauth", ctx.principal_id.value)

    def test_env_fallback_builds_default_credentials(self) -> None:
        settings = _settings(api_key="read-key", api_key_write="write-key")
        credentials = load_api_credentials(settings)
        self.assertEqual(2, len(credentials))
        self.assertEqual("principal:read-default", credentials[0].principal_id.value)
        self.assertIn("history:read", credentials[0].scopes)
        self.assertIn("workbench:read", credentials[0].scopes)
        self.assertIn("history:write", credentials[1].scopes)
        self.assertIn("sandbox:execute", credentials[1].scopes)
        self.assertIn("workbench:write", credentials[1].scopes)
        self.assertIn("workbench:export", credentials[1].scopes)

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

    def test_secret_sha256_credentials_resolve_without_plaintext_storage(self) -> None:
        settings = _settings(
            api_credentials_json="""
            [
              {
                "credential_id": "cred-1",
                "secret_sha256": "8ed3f6ad685b959ead7022518e1af76cd816f8e8ec7ccdda1ed4018e8f2223f8",
                "principal_id": "principal:alpha",
                "tenant_id": "tenant:a",
                "status": "active",
                "scopes": ["history:read"]
              }
            ]
            """,
        )

        credential = resolve_credential(provided_api_key="alpha", settings=settings)

        self.assertIsNotNone(credential)
        assert credential is not None
        self.assertEqual("cred-1", credential.credential_id)
        self.assertEqual(
            "8ed3f6ad685b959ead7022518e1af76cd816f8e8ec7ccdda1ed4018e8f2223f8",
            credential.secret_sha256,
        )

    def test_duplicate_secret_hashes_are_rejected(self) -> None:
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
                "credential_id": "cred-2",
                "secret_sha256": "8ed3f6ad685b959ead7022518e1af76cd816f8e8ec7ccdda1ed4018e8f2223f8",
                "principal_id": "principal:b",
                "status": "active",
                "scopes": ["history:read"]
              }
            ]
            """,
        )

        with self.assertRaises(ValueError):
            load_api_credentials(settings)

    def test_secret_sha256_must_be_valid_hex(self) -> None:
        settings = _settings(
            api_credentials_json="""
            [
              {
                "credential_id": "cred-1",
                "secret_sha256": "not-a-digest",
                "principal_id": "principal:a",
                "status": "active",
                "scopes": ["history:read"]
              }
            ]
            """,
        )

        with self.assertRaises(ValueError):
            load_api_credentials(settings)

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
