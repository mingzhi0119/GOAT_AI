from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.services.browser_access_session import (
    build_shared_access_authorization_context,
    decode_shared_access_session,
    encode_shared_access_session,
    issue_shared_access_session,
)
from goat_ai.config.settings import Settings


def _settings() -> Settings:
    return Settings(
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
        shared_access_password="goat-shared",
        shared_access_session_secret="session-secret",
        ready_skip_ollama_probe=True,
    )


class BrowserAccessSessionTests(unittest.TestCase):
    def test_issue_encode_decode_round_trip(self) -> None:
        settings = _settings()
        now = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)

        session = issue_shared_access_session(settings, now=now)
        encoded = encode_shared_access_session(session=session, settings=settings)
        decoded = decode_shared_access_session(encoded, settings=settings, now=now)

        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(session.owner_id, decoded.owner_id)
        self.assertEqual(session.principal_id, decoded.principal_id)
        self.assertEqual(session.issued_at, decoded.issued_at)
        self.assertEqual(session.expires_at, decoded.expires_at)

    def test_decode_rejects_tampered_cookie(self) -> None:
        settings = _settings()
        now = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
        session = issue_shared_access_session(settings, now=now)
        encoded = encode_shared_access_session(session=session, settings=settings)

        tampered = encoded[:-1] + ("A" if encoded[-1] != "A" else "B")

        self.assertIsNone(
            decode_shared_access_session(tampered, settings=settings, now=now)
        )

    def test_build_shared_access_authorization_context_uses_browser_identity(
        self,
    ) -> None:
        settings = _settings()
        session = issue_shared_access_session(
            settings,
            now=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
        )

        ctx = build_shared_access_authorization_context(session)

        self.assertEqual(session.owner_id, ctx.legacy_owner_id)
        self.assertEqual(session.principal_id, ctx.principal_id.value)
        self.assertEqual(
            f"credential:shared-access:{session.owner_id}",
            ctx.credential_id,
        )
        self.assertEqual("shared_access_cookie_v1", ctx.auth_mode)


if __name__ == "__main__":
    unittest.main()
