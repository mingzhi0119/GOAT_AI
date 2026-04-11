from __future__ import annotations

import unittest

from backend.models.chat import ChatMessage, ChatRequest
from backend.services.chat_message_merge import merge_request_image_attachments


class ChatMessageMergeTests(unittest.TestCase):
    def test_merges_request_attachments_into_last_user_message(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[
                ChatMessage(
                    role="user", content="Earlier", image_attachment_ids=["att-1"]
                ),
                ChatMessage(role="assistant", content="Ack"),
                ChatMessage(role="user", content="Latest"),
            ],
            image_attachment_ids=["att-2", "att-3"],
        )

        merged = merge_request_image_attachments(req)

        self.assertEqual(["att-1"], merged[0].image_attachment_ids)
        self.assertEqual(["att-2", "att-3"], merged[-1].image_attachment_ids)

    def test_dedupes_existing_and_request_attachment_ids(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[
                ChatMessage(
                    role="user",
                    content="Latest",
                    image_attachment_ids=["att-1", "att-2"],
                )
            ],
            image_attachment_ids=["att-2", "att-3"],
        )

        merged = merge_request_image_attachments(req)

        self.assertEqual(["att-1", "att-2", "att-3"], merged[0].image_attachment_ids)

    def test_leaves_messages_unchanged_when_there_is_no_user_turn(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="assistant", content="Ack")],
            image_attachment_ids=["att-1"],
        )

        merged = merge_request_image_attachments(req)

        self.assertEqual([], merged[0].image_attachment_ids)

    def test_leaves_messages_unchanged_when_request_has_no_attachments(self) -> None:
        req = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Latest")],
        )

        merged = merge_request_image_attachments(req)

        self.assertEqual([], merged[0].image_attachment_ids)


if __name__ == "__main__":
    unittest.main()
