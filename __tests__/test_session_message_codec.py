"""Session payload codec: explicit file_context vs legacy content sniff."""
from __future__ import annotations

import unittest

from backend.models.chat import ChatMessage
from backend.services.session_message_codec import (
    FILE_CONTEXT_UPLOAD_PREFIX,
    build_session_payload,
    is_file_context_message,
)
from goat_ai.tools import CHART_DATA_CSV_MARKER, LEGACY_CSV_FENCE_SUBSTRING


class SessionMessageCodecTests(unittest.TestCase):
    def test_file_context_flag_does_not_require_csv_fence(self) -> None:
        msg = ChatMessage(role="user", content="tabular context body", file_context=True)
        self.assertTrue(is_file_context_message(msg))

    def test_legacy_upload_prompt_still_detected_without_flag(self) -> None:
        body = (
            f"{FILE_CONTEXT_UPLOAD_PREFIX}\n\n"
            f"{CHART_DATA_CSV_MARKER}:\n```\nx,y\n1,2\n```"
        )
        msg = ChatMessage(role="user", content=body, file_context=False)
        self.assertTrue(is_file_context_message(msg))
        self.assertIn(LEGACY_CSV_FENCE_SUBSTRING, body)

    def test_build_payload_stores_explicit_file_context_in_field(self) -> None:
        payload = build_session_payload(
            messages=[
                ChatMessage(role="user", content="fc body", file_context=True),
                ChatMessage(role="user", content="visible ask"),
            ],
            assistant_text="ok",
            chart_spec=None,
            chart_data_source="none",
        )
        self.assertEqual(payload.get("file_context_prompt"), "fc body")
        raw_msgs = payload.get("messages")
        assert isinstance(raw_msgs, list)
        self.assertEqual(len(raw_msgs), 2)
        self.assertEqual(raw_msgs[0], {"role": "user", "content": "visible ask"})
        self.assertEqual(raw_msgs[1], {"role": "assistant", "content": "ok"})


if __name__ == "__main__":
    unittest.main()
