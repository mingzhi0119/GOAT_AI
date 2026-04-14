"""Create one pre-provisioned local account in the runtime metadata store."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import secrets

from backend.services.account_repository import AccountUser, normalize_account_email
from backend.services.password_hashing import hash_password
from backend.services.runtime_persistence import build_account_repository
from goat_ai.config.settings import load_settings


def _default_display_name(email: str) -> str:
    return email.split("@", 1)[0]


def _prompt_password() -> str:
    password = getpass.getpass("Password: ").strip()
    confirm = getpass.getpass("Confirm password: ").strip()
    if not password:
        raise SystemExit("Password is required.")
    if password != confirm:
        raise SystemExit("Passwords did not match.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one local browser-login account in the runtime metadata store."
    )
    parser.add_argument("--email", required=True, help="Account email address.")
    parser.add_argument(
        "--display-name",
        default="",
        help="Optional display name. Defaults to the email local-part.",
    )
    parser.add_argument(
        "--password",
        default="",
        help="Optional password. If omitted, the command prompts securely.",
    )
    args = parser.parse_args()

    settings = load_settings()
    repository = build_account_repository(settings)
    email = normalize_account_email(args.email)
    if repository.get_user_by_email(email) is not None:
        raise SystemExit(f"Account already exists for {email}.")

    password = args.password.strip() or _prompt_password()
    current = datetime.now(timezone.utc).isoformat()
    user = AccountUser(
        id=secrets.token_urlsafe(18),
        email=email,
        password_hash=hash_password(password),
        display_name=args.display_name.strip() or _default_display_name(email),
        primary_provider="local",
        created_at=current,
        updated_at=current,
    )
    repository.create_user(user)
    print(f"Created local account: {email}")


if __name__ == "__main__":
    main()
