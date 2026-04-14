from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.application.chat import _resolve_base_system_prompt
from backend.models.chat import ChatMessage, ChatRequest
from backend.services.chat_orchestration import PromptComposer
from goat_ai.config.settings import default_system_prompt_for_theme
from backend.routers.chat_options import (
    build_ollama_options,
    ollama_options_from_chat_request,
)


class ChatOptionsTests(unittest.TestCase):
    def test_build_empty_returns_none(self) -> None:
        self.assertIsNone(build_ollama_options())

    def test_build_maps_num_predict(self) -> None:
        o = build_ollama_options(
            temperature=0.7, max_tokens=512, top_p=0.95, think="high"
        )
        assert o is not None
        self.assertEqual(0.7, o["temperature"])
        self.assertEqual(512, o["num_predict"])
        self.assertEqual(0.95, o["top_p"])
        self.assertEqual("high", o["think"])

    def test_from_request(self) -> None:
        req = ChatRequest(
            model="m",
            messages=[ChatMessage(role="user", content="hi")],
            temperature=0.5,
            max_tokens=128,
            top_p=0.9,
            think="medium",
            plan_mode=True,
        )
        o = ollama_options_from_chat_request(req)
        assert o is not None
        self.assertEqual(0.5, o["temperature"])
        self.assertEqual(128, o["num_predict"])
        self.assertEqual("medium", o["think"])

    def test_plan_mode_composes_prompt_prefix(self) -> None:
        prompt = PromptComposer().compose(
            base_prompt="Base prompt",
            user_name="Simon",
            system_instruction="Be concise.",
            plan_mode=True,
        )
        self.assertIn("Plan mode is enabled.", prompt)
        self.assertIn("Simon", prompt)
        self.assertIn("Be concise.", prompt)
        self.assertIn("lower priority than the base system instructions", prompt)
        self.assertIn("Use `$...$` for inline math", prompt)
        self.assertIn("do not emit bare mathematical expressions", prompt)
        self.assertIn("If the user asks for a downloadable file", prompt)
        self.assertIn("[report.md](report.md)", prompt)

    def test_theme_default_prompts_vary_by_theme(self) -> None:
        classic = default_system_prompt_for_theme("classic")
        urochester = default_system_prompt_for_theme("urochester")
        thu = default_system_prompt_for_theme("thu")

        self.assertIn("general-purpose assistant", classic)
        self.assertIn("Simon Business School", urochester)
        self.assertIn("Tsinghua University", thu)

    def test_request_accepts_theme_style(self) -> None:
        req = ChatRequest(
            model="m",
            messages=[ChatMessage(role="user", content="hi")],
            theme_style="thu",
        )
        self.assertEqual("thu", req.theme_style)

    def test_theme_style_controls_default_base_prompt(self) -> None:
        req = ChatRequest(
            model="m",
            messages=[ChatMessage(role="user", content="hi")],
            theme_style="urochester",
        )
        settings = SimpleNamespace(
            system_prompt="legacy",
            system_prompt_overridden=False,
        )
        prompt = _resolve_base_system_prompt(req, settings)
        self.assertIn("Simon Business School", prompt)

    def test_explicit_system_prompt_override_wins_over_theme(self) -> None:
        req = ChatRequest(
            model="m",
            messages=[ChatMessage(role="user", content="hi")],
            theme_style="thu",
        )
        settings = SimpleNamespace(
            system_prompt="Custom prompt",
            system_prompt_overridden=True,
        )
        self.assertEqual("Custom prompt", _resolve_base_system_prompt(req, settings))


if __name__ == "__main__":
    unittest.main()
