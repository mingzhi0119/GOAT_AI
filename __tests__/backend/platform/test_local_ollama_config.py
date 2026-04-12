from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import goat_ai.config.settings as config


class LocalOllamaConfigTests(unittest.TestCase):
    def test_default_uses_local_sibling_ollama_when_present(self) -> None:
        with (
            patch.object(config, "LOCAL_OLLAMA_INSTALL_DIR", Path("/tmp/ollama")),
            patch.object(config, "LOCAL_OLLAMA_RUNTIME_DIR", Path("/tmp/ollama-local")),
            patch.object(config, "_has_local_ollama_layout", return_value=True),
        ):
            self.assertEqual(
                "http://127.0.0.1:11435", config._default_ollama_base_url()
            )

    def test_default_falls_back_to_shared_server_when_local_missing(self) -> None:
        with patch.object(config, "_has_local_ollama_layout", return_value=False):
            self.assertEqual(
                "http://127.0.0.1:11434", config._default_ollama_base_url()
            )

    def test_explicit_env_override_wins_over_local_default(self) -> None:
        original = os.environ.get("OLLAMA_BASE_URL")
        try:
            os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9999"
            with patch.object(config, "_has_local_ollama_layout", return_value=True):
                settings = config.load_settings()
            self.assertEqual("http://127.0.0.1:9999", settings.ollama_base_url)
        finally:
            if original is None:
                os.environ.pop("OLLAMA_BASE_URL", None)
            else:
                os.environ["OLLAMA_BASE_URL"] = original


if __name__ == "__main__":
    unittest.main()
