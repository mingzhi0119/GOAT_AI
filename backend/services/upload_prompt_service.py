from __future__ import annotations

from backend.models.knowledge import KnowledgeSearchRequest
from backend.services.knowledge_pipeline import normalize_document
from backend.services.knowledge_service import search_knowledge
from backend.types import LLMClient
from goat_ai.config import Settings

DEFAULT_PROMPT_RECOMMENDER_MODEL = "gemma4:26b"
_MAX_EVIDENCE_CHARS = 2400
_MAX_TEMPLATE_PROMPT_CHARS = 220

_SUFFIX_PROMPTS: dict[str, str] = {
    "csv": "Inspect this CSV for trends, anomalies, and key comparisons.",
    "xlsx": "Inspect this spreadsheet for trends, anomalies, and key comparisons.",
    "txt": "Summarize this text file and highlight the most important details.",
    "md": "Summarize this document and extract the main takeaways.",
    "pdf": "Summarize this PDF and cite the key evidence behind each point.",
    "docx": "Summarize this document and extract the main takeaways.",
}

_TEMPLATE_FALLBACKS: dict[str, str] = {
    "csv": "Analyze this CSV and tell me the main trends, outliers, and comparisons worth noting.",
    "xlsx": "Analyze this spreadsheet and tell me the main trends, outliers, and comparisons worth noting.",
    "txt": "Summarize this text file, identify the key themes, and recommend what to do next.",
    "md": "Summarize this document, identify the key themes, and recommend what to do next.",
    "pdf": "Summarize this PDF, identify the key arguments, and recommend what to do next.",
    "docx": "Summarize this document, identify the key arguments, and recommend what to do next.",
}


def file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def build_suffix_prompt(filename: str) -> str:
    ext = file_extension(filename)
    if ext in _SUFFIX_PROMPTS:
        return _SUFFIX_PROMPTS[ext]
    return "Tell me what this file contains and how I should analyze it."


def build_template_fallback_prompt(filename: str) -> str:
    ext = file_extension(filename)
    if ext in _TEMPLATE_FALLBACKS:
        return _TEMPLATE_FALLBACKS[ext]
    return "Analyze this file and suggest the best follow-up prompt for exploring its contents."


def recommend_template_prompt(
    *,
    llm: LLMClient | None,
    settings: Settings,
    document_id: str,
    filename: str,
) -> str:
    query = _retrieval_query_for_extension(file_extension(filename))
    evidence = _build_retrieval_evidence(
        settings=settings,
        document_id=document_id,
        filename=filename,
        query=query,
    )
    prompt = _build_recommendation_prompt(
        filename=filename,
        evidence=evidence,
    )

    if llm is not None:
        try:
            completion = llm.generate_completion(
                DEFAULT_PROMPT_RECOMMENDER_MODEL, prompt
            )
            cleaned = _clean_prompt_text(completion)
            if cleaned:
                return cleaned
        except Exception:
            pass

    return build_template_fallback_prompt(filename)


def _retrieval_query_for_extension(ext: str) -> str:
    if ext in {"csv", "xlsx"}:
        return "Identify trends, outliers, and key comparisons in this spreadsheet."
    return "Identify the main themes, decisions, and actionable takeaways in this document."


def _build_retrieval_evidence(
    *,
    settings: Settings,
    document_id: str,
    filename: str,
    query: str,
) -> str:
    try:
        response = search_knowledge(
            request=KnowledgeSearchRequest(
                query=query,
                document_ids=[document_id],
                top_k=4,
                retrieval_profile="rag3_quality",
            ),
            settings=settings,
        )
        snippets = [
            f"- {hit.snippet.strip()}" for hit in response.hits if hit.snippet.strip()
        ]
        if snippets:
            return "\n".join(snippets)[:_MAX_EVIDENCE_CHARS]
    except Exception:
        pass

    try:
        text = normalize_document(
            settings=settings, document_id=document_id, filename=filename
        )
    except Exception:
        return ""
    return text[:_MAX_EVIDENCE_CHARS]


def _build_recommendation_prompt(*, filename: str, evidence: str) -> str:
    ext = file_extension(filename)
    suffix_prompt = build_suffix_prompt(filename)
    file_type = ext.upper() if ext else "unknown"
    return (
        "You are generating a clickable template prompt for a chat UI.\n"
        f"File name: {filename}\n"
        f"File type: {file_type}\n"
        f"Suggested analysis angle: {suffix_prompt}\n\n"
        "Use the retrieved file content below as evidence. Write exactly one concise template prompt "
        "that a user can click to analyze this file. Keep it specific to the content, and return only the prompt text.\n\n"
        f"Retrieved content:\n{evidence or '(no retrievable text available)'}"
    )


def _clean_prompt_text(text: str) -> str:
    cleaned = " ".join(
        segment.strip() for segment in text.splitlines() if segment.strip()
    )
    cleaned = cleaned.strip().strip('"').strip("'").strip()
    if len(cleaned) > _MAX_TEMPLATE_PROMPT_CHARS:
        cleaned = cleaned[:_MAX_TEMPLATE_PROMPT_CHARS].rstrip()
    return cleaned
