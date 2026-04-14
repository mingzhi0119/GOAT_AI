from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from goat_ai.llm.public_model_policy import (
    public_model_allowlist,
)
from goat_ai.config.settings import Settings

from backend.services.public_model_policy import (
    filter_model_names_for_deployment,
    require_model_name_for_deployment,
)
from backend.services.exceptions import ModelNotAllowed


def _settings(*, deploy_mode: int) -> Settings:
    root = Path(tempfile.mkdtemp())
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        deploy_mode=deploy_mode,
    )


def test_public_model_allowlist_defaults_to_public_deploy_set() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert public_model_allowlist() == (
            "qwen3:4b",
            "llama3.2:3b",
            "gemma3:4b",
            "qwen2.5-coder:3b",
        )


def test_remote_public_model_policy_rejects_removed_gemma_alias() -> None:
    with patch.dict("os.environ", {}, clear=True):
        settings = _settings(deploy_mode=2)
        try:
            require_model_name_for_deployment("gemma4:26B", settings=settings)
        except ModelNotAllowed:
            return
        raise AssertionError(
            "expected removed Gemma alias to be rejected in remote mode"
        )


def test_remote_public_model_policy_filters_installed_models_in_public_order() -> None:
    with patch.dict("os.environ", {}, clear=True):
        settings = _settings(deploy_mode=2)
        assert filter_model_names_for_deployment(
            ["gemma4:26b", "rogue-model", "qwen3:4b"], settings=settings
        ) == ["qwen3:4b"]


def test_local_deploy_sees_all_installed_models() -> None:
    settings = _settings(deploy_mode=0)

    assert filter_model_names_for_deployment(
        ["gemma4:26b", "rogue-model", "qwen3:4b"], settings=settings
    ) == ["gemma4:26b", "rogue-model", "qwen3:4b"]


def test_local_deploy_accepts_non_public_model_names() -> None:
    settings = _settings(deploy_mode=0)

    assert (
        require_model_name_for_deployment("rogue-model", settings=settings)
        == "rogue-model"
    )
