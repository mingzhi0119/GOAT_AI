"""Session persistence and title-generation helpers for chat flows."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.models.chat import ChatMessage
from backend.services.chat_runtime import SessionRepository, SessionUpsertPayload, TitleGenerator
from backend.services.session_message_codec import ChartDataSource, build_session_payload, is_file_context_message

logger = logging.getLogger(__name__)


def last_user_message(messages: list[ChatMessage]) -> str:
    """Return the content of the final role=user message, or empty string."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def build_session_title_fallback(messages: list[ChatMessage]) -> str:
    """Fallback title from the last user message when no model title is available."""
    for msg in reversed(messages):
        if msg.role == "user":
            text = msg.content.strip().replace("\n", " ")
            return (text[:80] + "…") if len(text) > 80 else text
    return "New Chat"


def session_title_for_upsert(
    *,
    messages: list[ChatMessage],
    assistant_text: str,
    session_id: str,
    model: str,
    session_repository: SessionRepository,
    title_generator: TitleGenerator,
) -> str:
    """Resolve the title that should be stored for a chat session."""
    existing = session_repository.get_session(session_id)
    if existing is not None and existing.title.strip():
        return existing.title

    last_user = last_user_message(messages)
    if last_user and assistant_text.strip():
        try:
            generated = title_generator.generate_title(
                model=model,
                user_text=last_user,
                assistant_text=assistant_text,
            )
        except Exception:
            logger.exception("Session title generation failed")
            generated = None
        if generated:
            return generated
    return build_session_title_fallback(messages)


def persist_chat_session(
    *,
    session_id: str,
    model: str,
    final_messages: list[ChatMessage],
    assistant_text: str,
    chart_spec: dict[str, object] | None,
    session_repository: SessionRepository,
    title_generator: TitleGenerator,
    chart_data_source: ChartDataSource = "none",
    title_override: str | None = None,
) -> None:
    """Persist the latest session snapshot, including optional chart state."""
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = session_repository.get_session(session_id)
    created_at = existing.created_at if existing is not None else now_iso
    title = (
        title_override
        if title_override is not None
        else session_title_for_upsert(
            messages=final_messages,
            assistant_text=assistant_text,
            session_id=session_id,
            model=model,
            session_repository=session_repository,
            title_generator=title_generator,
        )
    )
    resolved_chart_data_source: ChartDataSource = chart_data_source
    if resolved_chart_data_source == "none" and any(is_file_context_message(msg) for msg in final_messages):
        resolved_chart_data_source = "uploaded"

    payload = build_session_payload(
        messages=final_messages,
        assistant_text=assistant_text,
        chart_spec=chart_spec,
        chart_data_source=resolved_chart_data_source,
    )

    session_repository.upsert_session(
        SessionUpsertPayload(
            session_id=session_id,
            title=title,
            model=model,
            schema_version=int(payload.get("version", 1)),
            payload=payload,
            created_at=created_at,
            updated_at=now_iso,
        )
    )
