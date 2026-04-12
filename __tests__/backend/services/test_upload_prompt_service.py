from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.upload_prompt_service import (
    _build_retrieval_evidence,
    build_suffix_prompt,
    build_template_fallback_prompt,
    recommend_template_prompt,
)
from goat_ai.config import Settings


class _FakeLLM:
    def __init__(self, completion: str | Exception) -> None:
        self._completion = completion

    def generate_completion(self, model: str, prompt: str) -> str:
        _ = (model, prompt)
        if isinstance(self._completion, Exception):
            raise self._completion
        return self._completion


def _settings() -> Settings:
    root = Path(tempfile.gettempdir()) / "goat-ai-upload-prompt-tests"
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
    )


class UploadPromptServiceTests(unittest.TestCase):
    def test_build_suffix_prompt_uses_extension_defaults(self) -> None:
        self.assertEqual(
            "Inspect this CSV for trends, anomalies, and key comparisons.",
            build_suffix_prompt("grades.csv"),
        )
        self.assertEqual(
            "Tell me what this file contains and how I should analyze it.",
            build_suffix_prompt("archive.bin"),
        )

    def test_build_template_fallback_prompt_uses_extension_defaults(self) -> None:
        self.assertEqual(
            "Summarize this PDF, identify the key arguments, and recommend what to do next.",
            build_template_fallback_prompt("memo.pdf"),
        )
        self.assertEqual(
            "Analyze this file and suggest the best follow-up prompt for exploring its contents.",
            build_template_fallback_prompt("archive.bin"),
        )

    def test_recommend_template_prompt_prefers_cleaned_llm_output(self) -> None:
        with patch(
            "backend.services.upload_prompt_service._build_retrieval_evidence",
            return_value="- evidence",
        ):
            prompt = recommend_template_prompt(
                llm=_FakeLLM(
                    '  "Summarize the quarterly revenue shifts and explain the outliers."\n'
                ),
                settings=_settings(),
                document_id="doc-1",
                filename="revenue.csv",
            )

        self.assertEqual(
            "Summarize the quarterly revenue shifts and explain the outliers.",
            prompt,
        )

    def test_recommend_template_prompt_falls_back_when_llm_fails(self) -> None:
        with patch(
            "backend.services.upload_prompt_service._build_retrieval_evidence",
            return_value="- evidence",
        ):
            prompt = recommend_template_prompt(
                llm=_FakeLLM(RuntimeError("llm unavailable")),
                settings=_settings(),
                document_id="doc-1",
                filename="notes.md",
            )

        self.assertEqual(
            "Summarize this document, identify the key themes, and recommend what to do next.",
            prompt,
        )

    def test_build_retrieval_evidence_falls_back_to_normalized_document(self) -> None:
        long_text = "A" * 3000
        with (
            patch(
                "backend.services.upload_prompt_service.search_knowledge",
                side_effect=RuntimeError("search unavailable"),
            ),
            patch(
                "backend.services.upload_prompt_service.normalize_document",
                return_value=long_text,
            ),
        ):
            evidence = _build_retrieval_evidence(
                settings=_settings(),
                document_id="doc-1",
                filename="memo.pdf",
                query="Summarize the document",
            )

        self.assertEqual(2400, len(evidence))
        self.assertEqual("A" * 2400, evidence)


if __name__ == "__main__":
    unittest.main()
