from __future__ import annotations

import unittest

from backend.models.chat import ChatMessage, ChatRequest
from backend.services.chat_orchestration import PromptComposer
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


if __name__ == "__main__":
    unittest.main()
