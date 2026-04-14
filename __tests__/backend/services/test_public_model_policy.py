from __future__ import annotations

from unittest.mock import patch

from goat_ai.llm.public_model_policy import (
    filter_public_model_names,
    public_model_allowlist,
    resolve_public_model_name,
)


def test_public_model_allowlist_defaults_to_public_deploy_set() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert public_model_allowlist() == (
            "qwen3:4b",
            "llama3.2:3b",
            "gemma3:4b",
            "qwen2.5-coder:3b",
        )


def test_public_model_policy_rejects_removed_gemma_alias() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert resolve_public_model_name("gemma4:26B") is None


def test_public_model_policy_filters_installed_models_in_public_order() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert filter_public_model_names(["gemma4:26b", "rogue-model", "qwen3:4b"]) == [
            "qwen3:4b",
        ]
