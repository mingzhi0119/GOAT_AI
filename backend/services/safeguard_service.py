"""Safeguard moderation boundary for chat — re-exports domain policy + adapter."""
from __future__ import annotations

from typing import Protocol

from backend.domain.safeguard_policy import (
    SAFEGUARD_BLOCKED_TITLE,
    SAFEGUARD_REFUSAL_MESSAGE,
    PolicyStage,
    RuleBasedSafeguardPolicy,
    SafeguardAssessment,
    SafeguardPolicy,
)
from backend.models.chat import ChatMessage
from backend.services.session_service import last_user_message

__all__ = [
    "SAFEGUARD_BLOCKED_TITLE",
    "SAFEGUARD_REFUSAL_MESSAGE",
    "PolicyStage",
    "RuleBasedSafeguardPolicy",
    "RuleBasedSafeguardService",
    "SafeguardAssessment",
    "SafeguardPolicy",
    "SafeguardService",
]


class SafeguardService(Protocol):
    """Typed moderation boundary for request/response text (service-layer Protocol)."""

    def review_input(
        self,
        *,
        messages: list[ChatMessage],
        system_instruction: str,
    ) -> SafeguardAssessment: ...

    def review_output(
        self,
        *,
        user_text: str,
        assistant_text: str,
    ) -> SafeguardAssessment: ...


class RuleBasedSafeguardService:
    """Adapter: builds candidate strings from chat messages, delegates to :class:`RuleBasedSafeguardPolicy`."""

    def __init__(self, *, policy: RuleBasedSafeguardPolicy | None = None) -> None:
        self._policy = policy or RuleBasedSafeguardPolicy()

    def review_input(
        self,
        *,
        messages: list[ChatMessage],
        system_instruction: str,
    ) -> SafeguardAssessment:
        candidate = "\n".join(
            [last_user_message(messages), system_instruction.strip()]
        ).strip()
        return self._policy.review_input_candidate(combined_user_and_system_text=candidate)

    def review_output(
        self,
        *,
        user_text: str,
        assistant_text: str,
    ) -> SafeguardAssessment:
        _ = user_text
        return self._policy.review_output_assistant_text(assistant_text=assistant_text)
