"""Rule-based safeguard policy — typed text in, :class:`SafeguardAssessment` out."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

PolicyStage = Literal["input", "output"]

SAFEGUARD_REFUSAL_MESSAGE = (
    "I can’t help with sexually explicit, violent, or otherwise unsafe content. "
    "I can help with a safer academic, policy, or wellbeing-focused alternative."
)
SAFEGUARD_BLOCKED_TITLE = "Blocked unsafe request"

_GENERATION_VERBS = re.compile(
    r"\b(write|generate|describe|depict|draw|create|roleplay|imagine|craft|story|scene)\b",
    re.IGNORECASE,
)
# Unambiguous terms — block on standalone occurrence in both input and output.
_EXPLICIT_SEXUAL_TERMS = re.compile(
    r"\b(porn|porno|nsfw|nude|naked|性交|色情|淫秽|做爱|强奸|rape|blowjob|handjob|cum|ejaculat|orgasm)\b",
    re.IGNORECASE,
)
# "explicit" is too generic to block alone (e.g. "be explicit about your ask",
# "explicitly state the terms").  Only block when it co-occurs with a clear
# sexual indicator within the same passage (up to 200 chars apart).
_EXPLICIT_SEXUAL_COMPOUND = re.compile(
    r"\bexplicit\b.{0,200}?\b(porn|porno|sex(?:ual)?|nude|naked|nsfw|erotic|adult.content|性|色情)\b|"
    r"\b(porn|porno|sex(?:ual)?|nude|naked|nsfw|erotic|adult.content|性|色情)\b.{0,200}?\bexplicit\b",
    re.IGNORECASE | re.DOTALL,
)
_MINOR_SEXUAL_TERMS = re.compile(
    r"\b(minor|child|kid|underage|teenager|loli|幼女|未成年)\b.*\b(sex|sexual|porn|nude|裸|性交|色情)\b|"
    r"\b(sex|sexual|porn|nude|裸|性交|色情)\b.*\b(minor|child|kid|underage|teenager|loli|幼女|未成年)\b",
    re.IGNORECASE,
)
_VIOLENT_INSTRUCTION_TERMS = re.compile(
    r"\b(how to|steps|instructions|guide|teach me|make a|build a|plan a)\b.*"
    r"\b(bomb|explosive|terror|terrorist|mass shooting|kill|murder|poison|arson)\b|"
    r"\b(bomb|explosive|terror|terrorist|mass shooting|kill|murder|poison|arson)\b.*"
    r"\b(how to|steps|instructions|guide|teach me|make a|build a|plan a)\b|"
    r"(炸弹|爆炸物|恐袭|恐怖袭击|投毒|纵火).*(怎么|如何|步骤|教程)|"
    r"(怎么|如何|步骤|教程).*(炸弹|爆炸物|恐袭|恐怖袭击|投毒|纵火)",
    re.IGNORECASE,
)
_TARGETED_THREAT_TERMS = re.compile(
    r"\b(kill|murder|rape|hurt|terrorize|doxx|blackmail)\b.*\b(him|her|them|my ex|teacher|student|professor)\b|"
    r"\b(i will|i want to|help me)\b.*\b(kill|murder|rape|hurt|terrorize)\b|"
    r"(我要|帮我|我想).*(杀|伤害|强奸|威胁)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SafeguardAssessment:
    """Decision returned by a safeguard policy check."""

    allowed: bool
    stage: PolicyStage
    reason_code: str | None = None
    refusal_message: str = SAFEGUARD_REFUSAL_MESSAGE


class SafeguardPolicy(Protocol):
    """Campus-facing moderation: combined user+system text (input) or assistant text (output)."""

    def review_input_candidate(
        self, *, combined_user_and_system_text: str
    ) -> SafeguardAssessment:
        """Assess the concatenated last user turn plus optional system instruction."""
        ...

    def review_output_assistant_text(
        self, *, assistant_text: str
    ) -> SafeguardAssessment:
        """Assess assistant output before streaming completion."""
        ...


def _matches_explicit_generation(text: str) -> bool:
    return bool(
        _GENERATION_VERBS.search(text)
        and (_EXPLICIT_SEXUAL_TERMS.search(text) or _EXPLICIT_SEXUAL_COMPOUND.search(text))
    )


def _contains_explicit_sexual_content(text: str) -> bool:
    return bool(_EXPLICIT_SEXUAL_TERMS.search(text) or _EXPLICIT_SEXUAL_COMPOUND.search(text))


class RuleBasedSafeguardPolicy:
    """Conservative keyword/regex policy; no network calls."""

    def review_input_candidate(
        self, *, combined_user_and_system_text: str
    ) -> SafeguardAssessment:
        candidate = combined_user_and_system_text.strip()
        if not candidate:
            return SafeguardAssessment(allowed=True, stage="input")
        if _MINOR_SEXUAL_TERMS.search(candidate):
            return SafeguardAssessment(
                allowed=False, stage="input", reason_code="sexual_minors"
            )
        if _matches_explicit_generation(candidate):
            return SafeguardAssessment(
                allowed=False, stage="input", reason_code="explicit_sexual"
            )
        if _VIOLENT_INSTRUCTION_TERMS.search(candidate):
            return SafeguardAssessment(
                allowed=False, stage="input", reason_code="violent_wrongdoing"
            )
        if _TARGETED_THREAT_TERMS.search(candidate):
            return SafeguardAssessment(
                allowed=False, stage="input", reason_code="targeted_threat"
            )
        return SafeguardAssessment(allowed=True, stage="input")

    def review_output_assistant_text(
        self, *, assistant_text: str
    ) -> SafeguardAssessment:
        candidate = assistant_text.strip()
        if not candidate:
            return SafeguardAssessment(allowed=True, stage="output")
        if _MINOR_SEXUAL_TERMS.search(candidate):
            return SafeguardAssessment(
                allowed=False, stage="output", reason_code="sexual_minors"
            )
        if _contains_explicit_sexual_content(candidate):
            return SafeguardAssessment(
                allowed=False, stage="output", reason_code="explicit_sexual"
            )
        if _VIOLENT_INSTRUCTION_TERMS.search(candidate):
            return SafeguardAssessment(
                allowed=False, stage="output", reason_code="violent_wrongdoing"
            )
        if _TARGETED_THREAT_TERMS.search(candidate):
            return SafeguardAssessment(
                allowed=False, stage="output", reason_code="targeted_threat"
            )
        return SafeguardAssessment(allowed=True, stage="output")
