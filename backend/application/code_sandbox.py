"""Code-sandbox gate use cases."""

from __future__ import annotations

from backend.application.ports import Settings
from backend.services.feature_gate_service import require_code_sandbox_enabled


def ensure_code_sandbox_enabled(settings: Settings) -> None:
    require_code_sandbox_enabled(settings)
