from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.dependencies import get_llm_client
from goat_ai.config import Settings
from goat_ai.ollama_client import OllamaService
from goat_ai.openai_client import OpenAIService


def _settings(root: Path, **kwargs: object) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="test-key",
        openai_models=("gpt-4.1-mini",),
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        **kwargs,
    )


class LLMProviderSelectionTests(unittest.TestCase):
    def test_defaults_to_ollama_client(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = get_llm_client(_settings(Path(tmp)))
            self.assertIsInstance(client, OllamaService)

    def test_selects_openai_client_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = get_llm_client(
                _settings(Path(tmp), llm_provider="openai")
            )
            self.assertIsInstance(client, OpenAIService)


if __name__ == "__main__":
    unittest.main()
