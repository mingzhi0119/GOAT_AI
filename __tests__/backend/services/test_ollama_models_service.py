"""Application-layer Ollama model helpers."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from goat_ai.shared.exceptions import OllamaUnavailable
from goat_ai.config.settings import Settings

from backend.services.exceptions import InferenceBackendUnavailable, ModelNotAllowed
from backend.services.ollama_models_service import (
    list_models_for_api,
    model_capabilities_for_api,
)


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


class OllamaModelsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.local_settings = _settings(deploy_mode=0)
        self.remote_settings = _settings(deploy_mode=2)

    def test_list_models_maps_ollama_down_to_domain_error(self) -> None:
        llm = MagicMock()
        llm.list_model_names.side_effect = OllamaUnavailable("offline")
        with self.assertRaises(InferenceBackendUnavailable):
            list_models_for_api(llm, settings=self.local_settings)

    def test_list_models_returns_all_models_for_local_deploy(self) -> None:
        llm = MagicMock()
        llm.list_model_names.return_value = ["qwen3:4b", "rogue-model", "gemma3:4b"]
        out = list_models_for_api(llm, settings=self.local_settings)
        self.assertEqual(out.models, ["qwen3:4b", "rogue-model", "gemma3:4b"])

    def test_list_models_filters_to_public_allowlist_for_remote_deploy(self) -> None:
        llm = MagicMock()
        llm.list_model_names.return_value = ["qwen3:4b", "rogue-model", "gemma3:4b"]
        out = list_models_for_api(llm, settings=self.remote_settings)
        self.assertEqual(out.models, ["qwen3:4b", "gemma3:4b"])

    def test_capabilities_maps_ollama_down_to_domain_error(self) -> None:
        llm = MagicMock()
        llm.describe_model_for_api.side_effect = OllamaUnavailable("offline")
        with self.assertRaises(InferenceBackendUnavailable):
            model_capabilities_for_api(llm, "qwen3:4b", settings=self.remote_settings)

    def test_capabilities_sets_tool_flags(self) -> None:
        llm = MagicMock()
        llm.describe_model_for_api.return_value = (["tools", "completion"], None)
        out = model_capabilities_for_api(llm, "qwen3:4b", settings=self.remote_settings)
        self.assertTrue(out.supports_tool_calling)
        self.assertTrue(out.supports_chart_tools)
        self.assertFalse(out.supports_vision)
        self.assertFalse(out.supports_thinking)
        self.assertIsNone(out.context_length)

    def test_capabilities_sets_vision_flag(self) -> None:
        llm = MagicMock()
        llm.describe_model_for_api.return_value = (["completion", "vision"], None)
        out = model_capabilities_for_api(
            llm, "gemma3:4b", settings=self.remote_settings
        )
        self.assertTrue(out.supports_vision)

    def test_capabilities_sets_thinking_flag(self) -> None:
        llm = MagicMock()
        llm.describe_model_for_api.return_value = (["completion", "thinking"], None)
        out = model_capabilities_for_api(
            llm, "gemma3:4B", settings=self.remote_settings
        )
        self.assertTrue(out.supports_thinking)
        self.assertEqual("gemma3:4b", out.model)

    def test_capabilities_passes_context_length(self) -> None:
        llm = MagicMock()
        llm.describe_model_for_api.return_value = (["completion"], 8192)
        out = model_capabilities_for_api(
            llm, "llama3.2:3b", settings=self.remote_settings
        )
        self.assertEqual(out.context_length, 8192)

    def test_remote_capabilities_reject_disallowed_models(self) -> None:
        llm = MagicMock()
        with self.assertRaises(ModelNotAllowed):
            model_capabilities_for_api(
                llm, "rogue-model", settings=self.remote_settings
            )

    def test_local_capabilities_allow_non_public_models(self) -> None:
        llm = MagicMock()
        llm.describe_model_for_api.return_value = (["completion"], 4096)

        out = model_capabilities_for_api(
            llm, "rogue-model", settings=self.local_settings
        )

        self.assertEqual("rogue-model", out.model)


if __name__ == "__main__":
    unittest.main()
