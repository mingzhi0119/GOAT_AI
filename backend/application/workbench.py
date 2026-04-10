"""Workbench task entrypoints."""

from __future__ import annotations

from backend.application.ports import Settings
from backend.services.feature_gate_service import require_agent_workbench_enabled


def ensure_agent_workbench_enabled(settings: Settings) -> None:
    """Enforce the shared runtime gate for future agent/workbench tasks."""
    require_agent_workbench_enabled(settings)
