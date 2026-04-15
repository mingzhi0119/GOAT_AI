"""Helpers for loading contract-generation settings in a stable local mode."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from collections.abc import Iterator

from goat_ai.config.settings import Settings, load_settings


@contextmanager
def _contract_env() -> Iterator[None]:
    original_deploy_mode = os.environ.get("GOAT_DEPLOY_MODE")
    original_runtime_root = os.environ.get("GOAT_RUNTIME_ROOT")

    with tempfile.TemporaryDirectory(prefix="goat-ai-contract-") as runtime_root:
        os.environ["GOAT_DEPLOY_MODE"] = "0"
        os.environ["GOAT_RUNTIME_ROOT"] = runtime_root
        try:
            yield
        finally:
            if original_deploy_mode is None:
                os.environ.pop("GOAT_DEPLOY_MODE", None)
            else:
                os.environ["GOAT_DEPLOY_MODE"] = original_deploy_mode

            if original_runtime_root is None:
                os.environ.pop("GOAT_RUNTIME_ROOT", None)
            else:
                os.environ["GOAT_RUNTIME_ROOT"] = original_runtime_root


def load_contract_settings() -> Settings:
    """Load settings for API contract generation in local mode."""
    with _contract_env():
        return load_settings()
