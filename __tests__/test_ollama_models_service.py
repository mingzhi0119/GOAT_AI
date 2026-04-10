"""Application-layer Ollama model helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from goat_ai.exceptions import OllamaUnavailable

from backend.services.exceptions import InferenceBackendUnavailable
from backend.services.ollama_models_service import (
    list_models_for_api,
    model_capabilities_for_api,
)


class OllamaModelsServiceTests(unittest.TestCase):
    def test_list_models_maps_ollama_down_to_domain_error(self) -> None:
        llm = MagicMock()
        llm.list_model_names.side_effect = OllamaUnavailable("offline")
        with self.assertRaises(InferenceBackendUnavailable):
            list_models_for_api(llm)

    def test_list_models_returns_models_response(self) -> None:
        llm = MagicMock()
        llm.list_model_names.return_value = ["a", "b"]
        out = list_models_for_api(llm)
        self.assertEqual(out.models, ["a", "b"])

    def test_capabilities_maps_ollama_down_to_domain_error(self) -> None:
        llm = MagicMock()
        llm.get_model_capabilities.side_effect = OllamaUnavailable("offline")
        with self.assertRaises(InferenceBackendUnavailable):
            model_capabilities_for_api(llm, "m")

    def test_capabilities_sets_tool_flags(self) -> None:
        llm = MagicMock()
        llm.get_model_capabilities.return_value = ["tools", "completion"]
        out = model_capabilities_for_api(llm, "m")
        self.assertTrue(out.supports_tool_calling)
        self.assertTrue(out.supports_chart_tools)
        self.assertFalse(out.supports_vision)
        self.assertFalse(out.supports_thinking)

    def test_capabilities_sets_vision_flag(self) -> None:
        llm = MagicMock()
        llm.get_model_capabilities.return_value = ["completion", "vision"]
        out = model_capabilities_for_api(llm, "m")
        self.assertTrue(out.supports_vision)

    def test_capabilities_sets_thinking_flag(self) -> None:
        llm = MagicMock()
        llm.get_model_capabilities.return_value = ["completion", "thinking"]
        out = model_capabilities_for_api(llm, "m")
        self.assertTrue(out.supports_thinking)


if __name__ == "__main__":
    unittest.main()
