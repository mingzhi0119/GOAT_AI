"""Prompt helpers for retrieval-backed knowledge synthesis."""

from __future__ import annotations

from backend.types import LLMClient

_DEFAULT_KNOWLEDGE_ANSWER_MODEL = "gemma4:26b"


def compose_knowledge_instruction(
    *,
    base_instruction: str,
    context_block: str,
    has_hits: bool,
) -> str:
    parts: list[str] = []
    if base_instruction.strip():
        parts.append(base_instruction.strip())
    if has_hits:
        parts.append(
            "Use the retrieved knowledge context below as your primary evidence. "
            "Answer naturally, synthesize rather than dumping snippets, and say when the context is insufficient.\n\n"
            "Retrieved knowledge context:\n"
            f"{context_block}"
        )
    else:
        parts.append(
            "No relevant retrieved context was found in the attached knowledge documents. "
            "Explain that briefly and suggest how the user can refine the question."
        )
    return "\n\n".join(parts)


def compose_knowledge_answer_prompt(
    *,
    query: str,
    context_block: str,
    has_hits: bool,
) -> str:
    return "\n\n".join(
        [
            "You are answering a user question with retrieved knowledge context.",
            "Return plain text only.",
            "Synthesize the evidence into a concise answer instead of listing raw snippets.",
            compose_knowledge_instruction(
                base_instruction="",
                context_block=context_block,
                has_hits=has_hits,
            ),
            f"User question:\n{query.strip()}",
        ]
    )


def resolve_knowledge_answer_model(llm: LLMClient) -> str:
    names = llm.list_model_names()
    return names[0] if names else _DEFAULT_KNOWLEDGE_ANSWER_MODEL
