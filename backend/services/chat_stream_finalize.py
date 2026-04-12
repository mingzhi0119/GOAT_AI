from __future__ import annotations

import logging
import time
from collections.abc import Generator

from backend.models.artifact import ChatArtifact
from backend.platform.prometheus_metrics import inc_chat_stream_completed
from backend.services.artifact_service import create_chat_artifacts_from_text
from backend.services.chat_stream_run import ChatStreamRunContext, strip_chart_block
from backend.services.exceptions import PersistenceReadError, PersistenceWriteError
from backend.services.safeguard_service import SafeguardAssessment
from backend.services.sse import sse_done_event, sse_error_event, sse_event

logger = logging.getLogger(__name__)


def phase_emit_completion(
    run: ChatStreamRunContext,
    error_message: str | None,
) -> Generator[str, None, None]:
    """After LLM phase: error tail, or safeguard output check + persist + done."""
    if run.input_blocked:
        return
    if error_message is not None:
        yield sse_done_event()
        return

    full_text = "".join(run.buffer)
    clean_text = strip_chart_block(full_text)
    chart_spec = run.emitted_chart_spec
    if not run.buffer:
        yield sse_error_event("The model produced no output.")
        yield sse_done_event()
        return

    output_assessment = (
        SafeguardAssessment(allowed=False, stage="output")
        if run.output_buffer.blocked
        else (
            run.safeguard.review_output(
                user_text=run.latest_user_text,
                assistant_text=clean_text,
            )
            if run.safeguard is not None
            else SafeguardAssessment(allowed=True, stage="output")
        )
    )
    if output_assessment.allowed:
        try:
            for token_event in run.output_buffer.flush():
                if run.first_token_emitted_at is None:
                    run.first_token_emitted_at = time.monotonic()
                yield token_event
            artifact_events = emit_artifacts(run, assistant_text=clean_text)
            for artifact in artifact_events:
                yield sse_event(
                    {
                        "type": "artifact",
                        **artifact.model_dump(mode="json"),
                    }
                )
            if chart_spec is not None:
                yield sse_event({"type": "chart_spec", "chart": chart_spec})
            first_token_ms = (
                round((run.first_token_emitted_at - run.started_at) * 1000, 1)
                if run.first_token_emitted_at is not None
                else None
            )
            run.persistence.persist_and_log_chat_result(
                model=run.model,
                messages=run.messages,
                system_prompt=run.system_prompt,
                ip=run.ip,
                conversation_logger=run.conversation_logger,
                user_name=run.user_name,
                session_id=run.session_id,
                all_messages=run.all_messages,
                session_repository=run.session_repository,
                title_generator=run.title_generator,
                assistant_text=clean_text,
                chart_spec=chart_spec,
                knowledge_documents=run.knowledge_documents,
                assistant_artifacts=[
                    artifact.model_dump(mode="json")
                    for artifact in run.emitted_artifacts
                ],
                chart_data_source=run.chart_data_source
                if chart_spec is not None
                else "none",
                started_at=run.started_at,
                first_token_ms=first_token_ms,
                session_owner_id=run.session_owner_id,
                tenant_id=run.tenant_id,
                principal_id=run.principal_id,
            )
        except (OSError, PersistenceReadError, PersistenceWriteError):
            logger.exception("Failed to persist completed chat result")
            yield sse_error_event("Failed to persist chat result.")
            yield sse_done_event()
            return
        yield sse_done_event()
        inc_chat_stream_completed()
        return

    yield from run.persistence.yield_blocked_response(
        assessment=output_assessment,
        model=run.model,
        messages=run.messages,
        system_prompt=run.system_prompt,
        ip=run.ip,
        conversation_logger=run.conversation_logger,
        user_name=run.user_name,
        session_id=run.session_id,
        all_messages=run.all_messages,
        session_repository=run.session_repository,
        title_generator=run.title_generator,
        started_at=run.started_at,
        session_owner_id=run.session_owner_id,
        tenant_id=run.tenant_id,
        principal_id=run.principal_id,
    )


def emit_artifacts(
    run: ChatStreamRunContext,
    *,
    assistant_text: str,
) -> list[ChatArtifact]:
    """Create and return any downloadable artifact events for this assistant turn."""
    if run.settings is None or run.session_repository is None:
        run.emitted_artifacts = []
        return []
    assistant_index = sum(1 for msg in run.messages if msg.role == "assistant")
    artifacts = create_chat_artifacts_from_text(
        assistant_text=assistant_text,
        settings=run.settings,
        session_id=run.session_id,
        owner_id=run.session_owner_id,
        tenant_id=run.tenant_id,
        principal_id=run.principal_id,
        source_message_index=assistant_index,
        register_artifact=run.session_repository.create_chat_artifact,
    )
    source_message_id = f"{run.session_id or 'ephemeral'}:assistant:{assistant_index}"
    run.emitted_artifacts = [
        artifact.model_copy(update={"source_message_id": source_message_id})
        for artifact in artifacts
    ]
    return run.emitted_artifacts
