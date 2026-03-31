from __future__ import annotations

import unittest

from backend.models.chat import ChatMessage, ChatRequest
from backend.routers.chat_options import build_ollama_options, ollama_options_from_chat_request


class ChatOptionsTests(unittest.TestCase):
    def test_build_empty_returns_none(self) -> None:
        self.assertIsNone(build_ollama_options())

    def test_build_maps_num_predict(self) -> None:
        o = build_ollama_options(temperature=0.7, max_tokens=512, top_p=0.95)
        assert o is not None
        self.assertEqual(0.7, o["temperature"])
        self.assertEqual(512, o["num_predict"])
        self.assertEqual(0.95, o["top_p"])

    def test_from_request(self) -> None:
        req = ChatRequest(
            model="m",
            messages=[ChatMessage(role="user", content="hi")],
            temperature=0.5,
            max_tokens=128,
            top_p=0.9,
        )
        o = ollama_options_from_chat_request(req)
        assert o is not None
        self.assertEqual(0.5, o["temperature"])
        self.assertEqual(128, o["num_predict"])


if __name__ == "__main__":
    unittest.main()
