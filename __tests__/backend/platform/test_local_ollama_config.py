from __future__ import annotations

import unittest
from unittest.mock import patch

import goat_ai.config.settings as config


class LocalOllamaConfigTests(unittest.TestCase):
    def test_default_uses_standard_local_ollama_port(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                "http://127.0.0.1:11434",
                config._default_ollama_base_url(),
            )

    def test_school_opt_in_switch_uses_school_local_ollama_port(self) -> None:
        with patch.dict(
            "os.environ", {"GOAT_USE_SCHOOL_OLLAMA_LOCAL": "1"}, clear=True
        ):
            self.assertEqual(
                "http://127.0.0.1:11435",
                config._default_ollama_base_url(),
            )

    def test_school_profile_alias_uses_school_local_ollama_port(self) -> None:
        with patch.dict(
            "os.environ",
            {"GOAT_OLLAMA_PROFILE": config.SCHOOL_OLLAMA_PROFILE},
            clear=True,
        ):
            self.assertEqual(
                "http://127.0.0.1:11435",
                config._default_ollama_base_url(),
            )

    def test_explicit_env_override_wins_over_school_default(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "GOAT_USE_SCHOOL_OLLAMA_LOCAL": "1",
                "OLLAMA_BASE_URL": "http://127.0.0.1:9999",
            },
            clear=True,
        ):
            settings = config.load_settings()
        self.assertEqual("http://127.0.0.1:9999", settings.ollama_base_url)


if __name__ == "__main__":
    unittest.main()
