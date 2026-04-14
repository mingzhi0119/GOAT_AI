from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from backend.services.account_auth import (
    authenticate_local_account,
    decode_account_session,
    issue_account_session,
    resolve_google_account,
)
from backend.services.account_repository import (
    AccountRepository,
    AccountUser,
    AccountUserIdentity,
    normalize_account_email,
)
from backend.services.password_hashing import hash_password
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
        account_auth_enabled=True,
        browser_session_secret="browser-secret",
        ready_skip_ollama_probe=True,
    )


class InMemoryAccountRepository(AccountRepository):
    def __init__(self) -> None:
        self.users: dict[str, AccountUser] = {}
        self.identities: dict[tuple[str, str], AccountUserIdentity] = {}

    def get_user_by_email(self, email: str) -> AccountUser | None:
        normalized = normalize_account_email(email)
        return next(
            (user for user in self.users.values() if user.email == normalized),
            None,
        )

    def get_user_by_id(self, user_id: str) -> AccountUser | None:
        return self.users.get(user_id)

    def get_user_by_identity(
        self, *, provider: str, provider_subject: str
    ) -> AccountUser | None:
        identity = self.identities.get((provider, provider_subject))
        if identity is None:
            return None
        return self.users.get(identity.user_id)

    def get_identity(
        self, *, provider: str, provider_subject: str
    ) -> AccountUserIdentity | None:
        return self.identities.get((provider, provider_subject))

    def create_user(self, user: AccountUser) -> None:
        self.users[user.id] = user

    def update_user(
        self,
        *,
        user_id: str,
        display_name: str,
        primary_provider: str,
        password_hash: str,
        updated_at: str,
    ) -> None:
        current = self.users[user_id]
        self.users[user_id] = replace(
            current,
            display_name=display_name,
            primary_provider=primary_provider,
            password_hash=password_hash,
            updated_at=updated_at,
        )

    def create_identity(self, identity: AccountUserIdentity) -> None:
        self.identities[(identity.provider, identity.provider_subject)] = identity


class AccountAuthServiceTests(unittest.TestCase):
    def test_issue_and_decode_account_session_round_trip(self) -> None:
        settings = _settings()
        user = AccountUser(
            id="user-1",
            email="user@example.com",
            password_hash=hash_password("secret"),
            display_name="User One",
            primary_provider="local",
            created_at="2026-04-14T12:00:00+00:00",
            updated_at="2026-04-14T12:00:00+00:00",
        )
        now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

        session = issue_account_session(
            user=user,
            provider="local",
            settings=settings,
            now=now,
        )
        decoded = decode_account_session(
            raw=__import__(
                "backend.services.account_auth", fromlist=["encode_account_session"]
            ).encode_account_session(session=session, settings=settings),
            settings=settings,
            now=now,
        )

        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(user.id, decoded.user_id)
        self.assertEqual(user.email, decoded.email)
        self.assertEqual("local", decoded.provider)

    def test_authenticate_local_account_requires_matching_password(self) -> None:
        repository = InMemoryAccountRepository()
        repository.create_user(
            AccountUser(
                id="user-1",
                email="user@example.com",
                password_hash=hash_password("secret"),
                display_name="User One",
                primary_provider="local",
                created_at="2026-04-14T12:00:00+00:00",
                updated_at="2026-04-14T12:00:00+00:00",
            )
        )

        self.assertIsNotNone(
            authenticate_local_account(
                repository,
                email="USER@example.com",
                password="secret",
            )
        )
        self.assertIsNone(
            authenticate_local_account(
                repository,
                email="user@example.com",
                password="wrong",
            )
        )

    def test_resolve_google_account_links_existing_local_user_by_email(self) -> None:
        repository = InMemoryAccountRepository()
        local_user = AccountUser(
            id="user-1",
            email="user@example.com",
            password_hash=hash_password("secret"),
            display_name="Local User",
            primary_provider="local",
            created_at="2026-04-14T12:00:00+00:00",
            updated_at="2026-04-14T12:00:00+00:00",
        )
        repository.create_user(local_user)

        resolved = resolve_google_account(
            repository,
            provider_subject="google-subject-1",
            email="user@example.com",
            display_name="Google User",
        )

        self.assertEqual(local_user.id, resolved.id)
        self.assertEqual("local", resolved.primary_provider)
        self.assertIsNotNone(
            repository.get_identity(
                provider="google",
                provider_subject="google-subject-1",
            )
        )


if __name__ == "__main__":
    unittest.main()
