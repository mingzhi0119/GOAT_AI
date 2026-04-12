"""Safeguard moderation boundary for chat - re-exports domain policy and adapter."""

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
    "ModeScopedSafeguardService",
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


_ALLOWED_INPUT = SafeguardAssessment(allowed=True, stage="input")
_ALLOWED_OUTPUT = SafeguardAssessment(allowed=True, stage="output")


class ModeScopedSafeguardService:
    """Wraps RuleBasedSafeguardService and suppresses one check direction based on mode.

    mode="input_only"  - review_output always returns allowed (only input is moderated)
    mode="output_only" - review_input always returns allowed (only output is moderated)
    mode="full"        - both checks active; identical to RuleBasedSafeguardService

    The factory in backend/platform/dependencies.py returns None for mode="off", so this
    class never needs to handle that case.
    """

    def __init__(self, *, mode: str) -> None:
        self._inner = RuleBasedSafeguardService()
        # mode is already validated by load_settings(); store for introspection/tests.
        self._mode = mode

    def review_input(
        self,
        *,
        messages: list[ChatMessage],
        system_instruction: str,
    ) -> SafeguardAssessment:
        if self._mode == "output_only":
            return _ALLOWED_INPUT
        return self._inner.review_input(
            messages=messages, system_instruction=system_instruction
        )

    def review_output(
        self,
        *,
        user_text: str,
        assistant_text: str,
    ) -> SafeguardAssessment:
        if self._mode == "input_only":
            return _ALLOWED_OUTPUT
        return self._inner.review_output(
            user_text=user_text, assistant_text=assistant_text
        )


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
        return self._policy.review_input_candidate(
            combined_user_and_system_text=candidate
        )

    def review_output(
        self,
        *,
        user_text: str,
        assistant_text: str,
    ) -> SafeguardAssessment:
        _ = user_text
        return self._policy.review_output_assistant_text(assistant_text=assistant_text)
