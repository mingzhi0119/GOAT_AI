"""LangGraph-backed multi-step research runtime for workbench retrieval tasks."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict

from backend.domain.authz_types import AuthorizationContext
from backend.models.knowledge import KnowledgeCitation, KnowledgeSearchRequest
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.knowledge_service import search_knowledge
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchTaskRepository,
)
from backend.services.workbench_source_registry import resolve_requested_sources
from backend.services.workbench_web_search import (
    WorkbenchWebSearchError,
    WorkbenchWebSearchHit,
    search_public_web,
)
from backend.services.workbench_readonly_retrieval import (
    WorkbenchConnectorBindingNotFound,
    search_connector_binding,
    search_project_memory,
)
from backend.types import LLMClient, Settings
from goat_ai.shared.exceptions import OllamaUnavailable

logger = logging.getLogger(__name__)

_DEFAULT_RESEARCH_MODEL = "gemma4:26b"
_MAX_SYNTHESIS_CITATIONS = 8


class WorkbenchResearchNoRunnableSources(RuntimeError):
    """Raised when the task resolves no runnable sources."""


class WorkbenchResearchExecutionFailed(RuntimeError):
    """Raised when every planned research step fails to run any source."""


@dataclass(frozen=True)
class WorkbenchResearchExecutionResult:
    """Final synthesized research result for browse/deep_research tasks."""

    result_text: str
    citations: list[KnowledgeCitation]


class _ResearchState(TypedDict):
    plan_steps: list[dict[str, str]]
    plan_strategy: str
    current_step_index: int
    runnable_source_ids: list[str]
    skipped_sources: list[dict[str, str]]
    accumulated_citations: list[KnowledgeCitation]
    completed_steps: list[dict[str, object]]
    successful_source_runs: int
    result_text: str
    should_continue: bool


def langgraph_runtime_available() -> bool:
    """Return whether LangGraph is importable in the current environment."""
    try:
        from langgraph.graph import END, START, StateGraph  # noqa: F401
    except ImportError:
        return False
    return True


def execute_langgraph_research_task(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    llm: LLMClient,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
    source_resolver: Callable[..., list[Any]] = resolve_requested_sources,
    knowledge_search: Callable[..., Any] = search_knowledge,
    web_search: Callable[..., list[WorkbenchWebSearchHit]] = search_public_web,
    project_memory_search: Callable[
        ..., list[KnowledgeCitation]
    ] = search_project_memory,
    connector_search: Callable[..., list[KnowledgeCitation]] = search_connector_binding,
) -> WorkbenchResearchExecutionResult:
    """Execute one browse/deep-research task through the LangGraph runtime."""
    graph = _compile_research_graph(
        task=task,
        repository=repository,
        llm=llm,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
        source_resolver=source_resolver,
        knowledge_search=knowledge_search,
        web_search=web_search,
        project_memory_search=project_memory_search,
        connector_search=connector_search,
    )
    final_state = graph.invoke(
        _ResearchState(
            plan_steps=[],
            plan_strategy="uninitialized",
            current_step_index=0,
            runnable_source_ids=[],
            skipped_sources=[],
            accumulated_citations=[],
            completed_steps=[],
            successful_source_runs=0,
            result_text="",
            should_continue=False,
        )
    )
    runnable_source_ids = list(final_state.get("runnable_source_ids", []))
    if not runnable_source_ids:
        raise WorkbenchResearchNoRunnableSources(
            "No runnable retrieval sources are currently available."
        )
    if int(final_state.get("successful_source_runs", 0)) < 1:
        raise WorkbenchResearchExecutionFailed("Retrieval execution failed.")

    result_text = str(final_state.get("result_text", "")).strip()
    citations = _dedupe_citations(list(final_state.get("accumulated_citations", [])))
    if not result_text:
        result_text = _compose_fallback_synthesis(
            task=task,
            plan_steps=list(final_state.get("plan_steps", [])),
            completed_steps=list(final_state.get("completed_steps", [])),
            citations=citations,
            runnable_source_ids=runnable_source_ids,
            skipped_sources=list(final_state.get("skipped_sources", [])),
        )
    return WorkbenchResearchExecutionResult(
        result_text=result_text,
        citations=citations,
    )


def _compile_research_graph(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    llm: LLMClient,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
    source_resolver: Callable[..., list[Any]],
    knowledge_search: Callable[..., Any],
    web_search: Callable[..., list[WorkbenchWebSearchHit]],
    project_memory_search: Callable[..., list[KnowledgeCitation]],
    connector_search: Callable[..., list[KnowledgeCitation]],
) -> Any:
    from langgraph.graph import END, START, StateGraph

    def resolve_sources_node(_: _ResearchState) -> dict[str, object]:
        resolved_sources = source_resolver(
            source_ids=task.source_ids,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
        runnable = [source for source in resolved_sources if source.runtime_ready]
        skipped = [
            {
                "source_id": source.source_id,
                "deny_reason": source.deny_reason or "not_runtime_ready",
            }
            for source in resolved_sources
            if not source.runtime_ready
        ]
        _append_task_event(
            repository=repository,
            task_id=task.id,
            event_type="retrieval.sources_resolved",
            status="running",
            message="Retrieval sources resolved.",
            metadata={
                "requested_source_ids": list(task.source_ids),
                "runnable_source_ids": [source.source_id for source in runnable],
                "skipped_sources": skipped,
                "runtime": "langgraph",
            },
        )
        for skipped_source in skipped:
            _append_task_event(
                repository=repository,
                task_id=task.id,
                event_type="retrieval.step.skipped",
                status="running",
                message=(
                    f"Skipped source {skipped_source['source_id']} "
                    f"({skipped_source['deny_reason']})."
                ),
                metadata={
                    **dict(skipped_source),
                    "runtime": "langgraph",
                },
            )
        return {
            "runnable_source_ids": [source.source_id for source in runnable],
            "skipped_sources": skipped,
        }

    def route_after_source_resolution(state: _ResearchState) -> str:
        if not state["runnable_source_ids"]:
            return END
        return "plan_research"

    def plan_research_node(_: _ResearchState) -> dict[str, object]:
        plan_steps, plan_strategy = _build_plan_steps(
            task=task, llm=llm, settings=settings
        )
        _append_task_event(
            repository=repository,
            task_id=task.id,
            event_type="research.plan.created",
            status="running",
            message=f"Planned {len(plan_steps)} bounded research step(s).",
            metadata={
                "runtime": "langgraph",
                "plan_strategy": plan_strategy,
                "step_queries": [step["query"] for step in plan_steps],
                "step_rationales": [step["rationale"] for step in plan_steps],
            },
        )
        return {
            "plan_steps": plan_steps,
            "plan_strategy": plan_strategy,
            "current_step_index": 0,
        }

    def execute_step_node(state: _ResearchState) -> dict[str, object]:
        plan_step = state["plan_steps"][state["current_step_index"]]
        step_number = state["current_step_index"] + 1
        query = plan_step["query"]
        rationale = plan_step["rationale"]
        _append_task_event(
            repository=repository,
            task_id=task.id,
            event_type="retrieval.step.started",
            status="running",
            message=f"Research step {step_number} started.",
            metadata={
                "runtime": "langgraph",
                "step_index": step_number,
                "query": query,
                "rationale": rationale,
            },
        )

        all_step_citations: list[KnowledgeCitation] = []
        completed_sources: list[str] = []
        source_failures: list[dict[str, str]] = []
        step_successful_source_runs = 0

        for source_id in state["runnable_source_ids"]:
            if source_id == "knowledge":
                try:
                    response = knowledge_search(
                        request=KnowledgeSearchRequest(
                            query=query,
                            document_ids=task.knowledge_document_ids,
                            top_k=8 if task.task_kind == "deep_research" else 5,
                            retrieval_profile=(
                                "rag3_quality"
                                if task.task_kind == "deep_research"
                                else "default"
                            ),
                        ),
                        settings=settings,
                        auth_context=auth_context,
                        request_id=request_id,
                    )
                except KnowledgeDocumentNotFound:
                    raise
                except Exception as exc:
                    logger.warning(
                        "Workbench knowledge research step failed",
                        extra={
                            "task_id": task.id,
                            "step_index": step_number,
                            "query": query,
                        },
                        exc_info=exc,
                    )
                    failure = {
                        "source_id": "knowledge",
                        "deny_reason": "provider_error",
                    }
                    source_failures.append(failure)
                    _append_task_event(
                        repository=repository,
                        task_id=task.id,
                        event_type="retrieval.step.skipped",
                        status="running",
                        message="Source knowledge failed to return results.",
                        metadata={
                            **failure,
                            "runtime": "langgraph",
                            "step_index": step_number,
                            "query": query,
                        },
                    )
                    continue

                all_step_citations.extend(response.hits)
                completed_sources.append("knowledge")
                step_successful_source_runs += 1
                _append_task_event(
                    repository=repository,
                    task_id=task.id,
                    event_type="retrieval.step.completed",
                    status="running",
                    message=(
                        f"Step {step_number} source knowledge returned "
                        f"{len(response.hits)} citations."
                    ),
                    metadata={
                        "runtime": "langgraph",
                        "step_index": step_number,
                        "query": query,
                        "source_id": "knowledge",
                        "citation_count": len(response.hits),
                        "effective_query": response.effective_query or query,
                    },
                )
                continue

            if source_id == "web":
                try:
                    web_hits = web_search(
                        query=query,
                        settings=settings,
                        max_results=_resolve_web_result_limit(
                            task_kind=task.task_kind,
                            settings=settings,
                        ),
                    )
                except WorkbenchWebSearchError:
                    failure = {"source_id": "web", "deny_reason": "provider_error"}
                    source_failures.append(failure)
                    _append_task_event(
                        repository=repository,
                        task_id=task.id,
                        event_type="retrieval.step.skipped",
                        status="running",
                        message="Source web failed to return results.",
                        metadata={
                            **failure,
                            "runtime": "langgraph",
                            "step_index": step_number,
                            "query": query,
                            "provider": settings.workbench_web_provider,
                        },
                    )
                    continue

                all_step_citations.extend(_web_hit_to_citation(hit) for hit in web_hits)
                completed_sources.append("web")
                step_successful_source_runs += 1
                _append_task_event(
                    repository=repository,
                    task_id=task.id,
                    event_type="retrieval.step.completed",
                    status="running",
                    message=(
                        f"Step {step_number} source web returned {len(web_hits)} citations."
                    ),
                    metadata={
                        "runtime": "langgraph",
                        "step_index": step_number,
                        "query": query,
                        "source_id": "web",
                        "citation_count": len(web_hits),
                        "provider": settings.workbench_web_provider,
                        "max_results": _resolve_web_result_limit(
                            task_kind=task.task_kind,
                            settings=settings,
                        ),
                        "urls": [hit.url for hit in web_hits[:5]],
                    },
                )
                continue

            if source_id == "project_memory":
                if not task.project_id:
                    failure = {
                        "source_id": "project_memory",
                        "deny_reason": "project_scope_missing",
                    }
                    source_failures.append(failure)
                    _append_task_event(
                        repository=repository,
                        task_id=task.id,
                        event_type="retrieval.step.skipped",
                        status="running",
                        message="Project memory requires an explicit project scope.",
                        metadata={
                            **failure,
                            "runtime": "langgraph",
                            "step_index": step_number,
                            "query": query,
                        },
                    )
                    continue
                try:
                    project_hits = project_memory_search(
                        task=task,
                        repository=repository,
                        settings=settings,
                        auth_context=auth_context,
                        query=query,
                    )
                except Exception as exc:
                    logger.warning(
                        "Workbench project-memory research step failed",
                        extra={
                            "task_id": task.id,
                            "step_index": step_number,
                            "query": query,
                        },
                        exc_info=exc,
                    )
                    failure = {
                        "source_id": "project_memory",
                        "deny_reason": "provider_error",
                    }
                    source_failures.append(failure)
                    _append_task_event(
                        repository=repository,
                        task_id=task.id,
                        event_type="retrieval.step.skipped",
                        status="running",
                        message="Source project_memory failed to return results.",
                        metadata={
                            **failure,
                            "runtime": "langgraph",
                            "step_index": step_number,
                            "query": query,
                        },
                    )
                    continue

                all_step_citations.extend(project_hits)
                completed_sources.append("project_memory")
                step_successful_source_runs += 1
                _append_task_event(
                    repository=repository,
                    task_id=task.id,
                    event_type="retrieval.step.completed",
                    status="running",
                    message=(
                        f"Step {step_number} source project_memory returned "
                        f"{len(project_hits)} citations."
                    ),
                    metadata={
                        "runtime": "langgraph",
                        "step_index": step_number,
                        "query": query,
                        "source_id": "project_memory",
                        "citation_count": len(project_hits),
                        "project_id": task.project_id,
                    },
                )
                continue

            if source_id.startswith("connector:"):
                try:
                    connector_hits = connector_search(
                        source_id=source_id,
                        task_kind=task.task_kind,
                        settings=settings,
                        query=query,
                    )
                except WorkbenchConnectorBindingNotFound:
                    failure = {
                        "source_id": source_id,
                        "deny_reason": "binding_unavailable",
                    }
                    source_failures.append(failure)
                    _append_task_event(
                        repository=repository,
                        task_id=task.id,
                        event_type="retrieval.step.skipped",
                        status="running",
                        message=f"Source {source_id} is no longer available.",
                        metadata={
                            **failure,
                            "runtime": "langgraph",
                            "step_index": step_number,
                            "query": query,
                        },
                    )
                    continue
                except Exception as exc:
                    logger.warning(
                        "Workbench connector research step failed",
                        extra={
                            "task_id": task.id,
                            "step_index": step_number,
                            "query": query,
                            "source_id": source_id,
                        },
                        exc_info=exc,
                    )
                    failure = {
                        "source_id": source_id,
                        "deny_reason": "provider_error",
                    }
                    source_failures.append(failure)
                    _append_task_event(
                        repository=repository,
                        task_id=task.id,
                        event_type="retrieval.step.skipped",
                        status="running",
                        message=f"Source {source_id} failed to return results.",
                        metadata={
                            **failure,
                            "runtime": "langgraph",
                            "step_index": step_number,
                            "query": query,
                        },
                    )
                    continue

                all_step_citations.extend(connector_hits)
                completed_sources.append(source_id)
                step_successful_source_runs += 1
                _append_task_event(
                    repository=repository,
                    task_id=task.id,
                    event_type="retrieval.step.completed",
                    status="running",
                    message=(
                        f"Step {step_number} source {source_id} returned "
                        f"{len(connector_hits)} citations."
                    ),
                    metadata={
                        "runtime": "langgraph",
                        "step_index": step_number,
                        "query": query,
                        "source_id": source_id,
                        "citation_count": len(connector_hits),
                    },
                )
                continue

            failure = {"source_id": source_id, "deny_reason": "no_executor"}
            source_failures.append(failure)
            _append_task_event(
                repository=repository,
                task_id=task.id,
                event_type="retrieval.step.skipped",
                status="running",
                message=f"Source {source_id} is registered but has no executor yet.",
                metadata={
                    **failure,
                    "runtime": "langgraph",
                    "step_index": step_number,
                    "query": query,
                },
            )

        accumulated_citations = _dedupe_citations(
            [*state["accumulated_citations"], *all_step_citations]
        )
        completed_steps = list(state["completed_steps"])
        completed_steps.append(
            {
                "step_index": step_number,
                "query": query,
                "rationale": rationale,
                "citation_count": len(all_step_citations),
                "completed_sources": list(completed_sources),
                "source_failures": list(source_failures),
                "successful_source_runs": step_successful_source_runs,
            }
        )
        return {
            "accumulated_citations": accumulated_citations,
            "completed_steps": completed_steps,
            "successful_source_runs": state["successful_source_runs"]
            + step_successful_source_runs,
        }

    def advance_or_finish_node(state: _ResearchState) -> dict[str, object]:
        next_step_index = state["current_step_index"] + 1
        completed_steps = state["completed_steps"]
        latest_step = completed_steps[-1] if completed_steps else {}
        accumulated_citations = len(state["accumulated_citations"])
        last_step_successes = int(latest_step.get("successful_source_runs", 0))
        should_continue = False

        if next_step_index < len(state["plan_steps"]) and last_step_successes > 0:
            if task.task_kind == "deep_research":
                should_continue = (
                    state["current_step_index"] == 0 or accumulated_citations < 8
                )
            else:
                should_continue = accumulated_citations < 2

        if should_continue:
            next_step = state["plan_steps"][next_step_index]
            _append_task_event(
                repository=repository,
                task_id=task.id,
                event_type="research.follow_up.scheduled",
                status="running",
                message=f"Scheduled follow-up research step {next_step_index + 1}.",
                metadata={
                    "runtime": "langgraph",
                    "step_index": next_step_index + 1,
                    "query": next_step["query"],
                    "rationale": next_step["rationale"],
                },
            )

        return {
            "current_step_index": next_step_index
            if should_continue
            else state["current_step_index"],
            "should_continue": should_continue,
        }

    def route_after_advance(state: _ResearchState) -> str:
        if state["successful_source_runs"] < 1 and not state["should_continue"]:
            return END
        if state["should_continue"]:
            return "execute_step"
        return "synthesize"

    def synthesize_node(state: _ResearchState) -> dict[str, object]:
        result_text, synthesis_strategy = _compose_synthesis(
            task=task,
            llm=llm,
            plan_steps=state["plan_steps"],
            completed_steps=state["completed_steps"],
            citations=state["accumulated_citations"],
            runnable_source_ids=state["runnable_source_ids"],
            skipped_sources=state["skipped_sources"],
        )
        _append_task_event(
            repository=repository,
            task_id=task.id,
            event_type="research.synthesis.completed",
            status="running",
            message="Research synthesis completed.",
            metadata={
                "runtime": "langgraph",
                "synthesis_strategy": synthesis_strategy,
                "step_count": len(state["completed_steps"]),
                "citation_count": len(state["accumulated_citations"]),
            },
        )
        return {"result_text": result_text}

    graph = StateGraph(_ResearchState)
    graph.add_node("resolve_sources", resolve_sources_node)
    graph.add_node("plan_research", plan_research_node)
    graph.add_node("execute_step", execute_step_node)
    graph.add_node("advance_or_finish", advance_or_finish_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_edge(START, "resolve_sources")
    graph.add_conditional_edges(
        "resolve_sources",
        route_after_source_resolution,
        {
            "plan_research": "plan_research",
            END: END,
        },
    )
    graph.add_edge("plan_research", "execute_step")
    graph.add_edge("execute_step", "advance_or_finish")
    graph.add_conditional_edges(
        "advance_or_finish",
        route_after_advance,
        {
            END: END,
            "execute_step": "execute_step",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("synthesize", END)
    return graph.compile()


def _build_plan_steps(
    *,
    task: WorkbenchTaskRecord,
    llm: LLMClient,
    settings: Settings,
) -> tuple[list[dict[str, str]], str]:
    max_steps = _resolve_max_steps(task.task_kind, settings)
    prompt = _compose_research_plan_prompt(task=task, max_steps=max_steps)
    try:
        raw = llm.generate_completion(_resolve_research_model(llm), prompt).strip()
    except OllamaUnavailable:
        return _fallback_plan_steps(
            task.prompt, max_steps=max_steps
        ), "fallback_ollama_unavailable"
    except Exception as exc:
        logger.warning(
            "Workbench research planning fell back to deterministic queries",
            extra={"task_id": task.id},
            exc_info=exc,
        )
        return _fallback_plan_steps(
            task.prompt, max_steps=max_steps
        ), "fallback_exception"

    parsed = _parse_plan_steps(raw, max_steps=max_steps)
    if parsed:
        return parsed, "llm"
    return _fallback_plan_steps(task.prompt, max_steps=max_steps), "fallback_parse"


def _compose_research_plan_prompt(
    *,
    task: WorkbenchTaskRecord,
    max_steps: int,
) -> str:
    return "\n".join(
        [
            "You are planning a bounded multi-step research task.",
            "Return JSON only.",
            'Use the shape {"queries":[{"query":"...","rationale":"..."}]}.',
            f"Return between 1 and {max_steps} distinct search queries.",
            "Query 1 should be broad coverage; later queries should probe risks, constraints, or contradictions.",
            "Do not include markdown fences or prose outside JSON.",
            f"Task kind: {task.task_kind}",
            f"User request: {task.prompt}",
        ]
    )


def _parse_plan_steps(raw: str, *, max_steps: int) -> list[dict[str, str]]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = "\n".join(candidate.splitlines()[1:-1]).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        candidate = candidate[start : end + 1]
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return []

    items = payload.get("queries", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []

    parsed: list[dict[str, str]] = []
    seen_queries: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        query = str(item.get("query", "")).strip()
        rationale = str(item.get("rationale", "")).strip() or "Follow-up angle"
        normalized = query.casefold()
        if not query or normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        parsed.append({"query": query[:180], "rationale": rationale[:180]})
        if len(parsed) >= max_steps:
            break
    return parsed


def _fallback_plan_steps(prompt: str, *, max_steps: int) -> list[dict[str, str]]:
    suffixes = [
        ("", "Primary overview query"),
        (" risks evidence", "Probe key risks and failure cases"),
        (
            " implementation constraints",
            "Probe implementation constraints and tradeoffs",
        ),
        (" counterexamples", "Probe contradictions or counterexamples"),
        (" operating guidance", "Probe operational guidance and prerequisites"),
    ]
    steps: list[dict[str, str]] = []
    seen: set[str] = set()
    for suffix, rationale in suffixes:
        query = f"{prompt}{suffix}".strip()
        normalized = query.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        steps.append({"query": query[:180], "rationale": rationale})
        if len(steps) >= max_steps:
            break
    return steps or [{"query": prompt[:180], "rationale": "Primary overview query"}]


def _compose_synthesis(
    *,
    task: WorkbenchTaskRecord,
    llm: LLMClient,
    plan_steps: list[dict[str, str]],
    completed_steps: list[dict[str, object]],
    citations: list[KnowledgeCitation],
    runnable_source_ids: list[str],
    skipped_sources: list[dict[str, str]],
) -> tuple[str, str]:
    expected_heading = (
        "## Browse Summary" if task.task_kind == "browse" else "## Research Brief"
    )
    prompt = _compose_synthesis_prompt(
        task=task,
        plan_steps=plan_steps,
        completed_steps=completed_steps,
        citations=citations,
        runnable_source_ids=runnable_source_ids,
        skipped_sources=skipped_sources,
    )
    try:
        result = llm.generate_completion(_resolve_research_model(llm), prompt).strip()
    except OllamaUnavailable:
        result = ""
        strategy = "fallback_ollama_unavailable"
    except Exception as exc:
        logger.warning(
            "Workbench research synthesis fell back to deterministic markdown",
            extra={"task_id": task.id},
            exc_info=exc,
        )
        result = ""
        strategy = "fallback_exception"
    else:
        strategy = "llm"

    if result and result.lstrip().startswith(expected_heading):
        return result, strategy
    return (
        _compose_fallback_synthesis(
            task=task,
            plan_steps=plan_steps,
            completed_steps=completed_steps,
            citations=citations,
            runnable_source_ids=runnable_source_ids,
            skipped_sources=skipped_sources,
        ),
        strategy,
    )


def _compose_synthesis_prompt(
    *,
    task: WorkbenchTaskRecord,
    plan_steps: list[dict[str, str]],
    completed_steps: list[dict[str, object]],
    citations: list[KnowledgeCitation],
    runnable_source_ids: list[str],
    skipped_sources: list[dict[str, str]],
) -> str:
    heading = "Browse Summary" if task.task_kind == "browse" else "Research Brief"
    step_lines = [
        (
            f"- Step {step['step_index']}: {step['query']} | "
            f"sources={', '.join(step['completed_sources']) or 'none'} | "
            f"citations={step['citation_count']}"
        )
        for step in completed_steps
    ]
    citation_lines = []
    for citation in citations[:_MAX_SYNTHESIS_CITATIONS]:
        snippet = citation.snippet.strip().replace("\n", " ")
        citation_lines.append(
            f"- {citation.filename} ({citation.document_id}): {snippet[:240].strip()}"
        )
    skipped = (
        ", ".join(
            f"{item['source_id']} ({item['deny_reason']})" for item in skipped_sources
        )
        or "none"
    )
    return "\n".join(
        [
            "You are synthesizing a bounded workbench research task.",
            "Return markdown only.",
            f"Start with exactly `## {heading}`.",
            "Then include these sections in order: Findings, Evidence, Remaining Gaps.",
            "Keep claims grounded in the evidence and mention uncertainty where needed.",
            f"User request: {task.prompt}",
            f"Planned steps: {json.dumps(plan_steps)}",
            "Completed steps:",
            *step_lines,
            f"Runnable sources: {', '.join(runnable_source_ids) or 'none'}",
            f"Deferred sources: {skipped}",
            "Evidence snippets:",
            *citation_lines,
        ]
    )


def _compose_fallback_synthesis(
    *,
    task: WorkbenchTaskRecord,
    plan_steps: list[dict[str, str]],
    completed_steps: list[dict[str, object]],
    citations: list[KnowledgeCitation],
    runnable_source_ids: list[str],
    skipped_sources: list[dict[str, str]],
) -> str:
    heading = "Browse Summary" if task.task_kind == "browse" else "Research Brief"
    lines = [
        f"## {heading}",
        f"- Query: {task.prompt}",
        f"- Planned steps: {len(plan_steps)}",
        f"- Executed steps: {len(completed_steps)}",
        "- Runnable sources: " + (", ".join(runnable_source_ids) or "none"),
    ]
    if skipped_sources:
        skipped = ", ".join(
            f"{item['source_id']} ({item['deny_reason']})" for item in skipped_sources
        )
        lines.append(f"- Deferred sources: {skipped}")

    lines.extend(["", "## Findings"])
    if not completed_steps:
        lines.append("- No research steps executed.")
    else:
        for step in completed_steps:
            lines.append(
                "- Step {step_index}: {query} | sources={sources} | citations={citation_count}".format(
                    step_index=step["step_index"],
                    query=step["query"],
                    sources=", ".join(step["completed_sources"]) or "none",
                    citation_count=step["citation_count"],
                )
            )

    if not citations:
        lines.extend(
            [
                "",
                "## Evidence",
                "- No relevant context was found in the currently runnable sources.",
                "",
                "## Remaining Gaps",
                "- Additional evidence collection is still needed before treating this as complete.",
            ]
        )
        return "\n".join(lines)

    lines.extend(["", "## Evidence"])
    for citation in citations:
        snippet = citation.snippet.strip().replace("\n", " ")
        bounded = snippet[:220].strip()
        if citation.document_id.startswith(("http://", "https://")):
            lines.append(f"- [{citation.filename}]({citation.document_id}): {bounded}")
        else:
            lines.append(f"- {citation.filename}: {bounded}")

    lines.extend(["", "## Remaining Gaps"])
    if task.task_kind == "deep_research" and len(
        completed_steps
    ) < _resolve_expected_deep_research_steps(len(plan_steps)):
        lines.append(
            "- Research stopped early because later follow-up steps were not runnable or not needed."
        )
    else:
        lines.append(
            "- Treat this as a bounded evidence brief, not a permanent substitute for human review."
        )
    return "\n".join(lines)


def _resolve_expected_deep_research_steps(planned_steps: int) -> int:
    if planned_steps <= 1:
        return 1
    return min(2, planned_steps)


def _resolve_research_model(llm: LLMClient) -> str:
    try:
        names = llm.list_model_names()
    except Exception:
        return _DEFAULT_RESEARCH_MODEL
    return names[0] if names else _DEFAULT_RESEARCH_MODEL


def _resolve_max_steps(task_kind: str, settings: Settings) -> int:
    if task_kind == "deep_research":
        return settings.workbench_deep_research_max_steps
    return settings.workbench_browse_max_steps


def _resolve_web_result_limit(*, task_kind: str, settings: Settings) -> int:
    default_limit = 8 if task_kind == "deep_research" else 5
    return min(default_limit, settings.workbench_web_max_results)


def _web_hit_to_citation(hit: WorkbenchWebSearchHit) -> KnowledgeCitation:
    return KnowledgeCitation(
        document_id=hit.url,
        chunk_id=hit.url,
        filename=hit.title,
        snippet=hit.snippet,
        score=max(0.0, 1.0 - ((hit.rank - 1) * 0.01)),
    )


def _dedupe_citations(citations: list[KnowledgeCitation]) -> list[KnowledgeCitation]:
    seen: set[tuple[str, str]] = set()
    out: list[KnowledgeCitation] = []
    for citation in citations:
        key = (citation.document_id, citation.chunk_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(citation)
    return out


def _append_task_event(
    *,
    repository: WorkbenchTaskRepository,
    task_id: str,
    event_type: str,
    status: str | None,
    message: str,
    metadata: dict[str, object] | None = None,
) -> None:
    repository.append_task_event(
        task_id,
        event_type=event_type,
        created_at=_now_iso(),
        status=status,
        message=message,
        metadata=metadata,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
