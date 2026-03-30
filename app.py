from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import requests
import streamlit as st

# --- Configuration (env-first; see docs/OPERATIONS.md and .env.example) ---
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
GENERATE_TIMEOUT = int(os.environ.get("OLLAMA_GENERATE_TIMEOUT", "120"))
MAX_UPLOAD_MB = int(os.environ.get("GOAT_MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_DATAFRAME_ROWS = int(os.environ.get("GOAT_MAX_DATAFRAME_ROWS", "50000"))
USE_CHAT_API = os.environ.get("GOAT_USE_CHAT_API", "true").lower() in ("1", "true", "yes")

_APP_DIR = Path(__file__).resolve().parent
_SIMON_LOGO_SVG = _APP_DIR / "static" / "urochester_simon_business_horizontal.svg"

_DEFAULT_SYSTEM_PROMPT = """You are GOAT AI, a helpful assistant for students and faculty at the University of Rochester Simon Business School.
You give clear, professional business-oriented analysis. You do not invent data: when tabular data is provided, cite its shape (rows/columns) and column names in your reasoning.
Stay neutral, educational, and policy-safe: no harmful, discriminatory, or non-academic misuse of content.
If you are unsure, say so briefly."""

SYSTEM_PROMPT = os.environ.get("GOAT_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT).strip()
_prompt_file = os.environ.get("GOAT_SYSTEM_PROMPT_FILE", "").strip()
if _prompt_file:
    _p = Path(_prompt_file)
    if _p.is_file():
        SYSTEM_PROMPT = _p.read_text(encoding="utf-8").strip()

USER_FACING_ERROR = "Sorry, the AI service is temporarily unavailable. Please try again or check that Ollama is running."

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )


_configure_logging()


# --- Tool-style helpers (agent loop: perceive → plan uses these summaries in the prompt) ---


def describe_dataframe(df: pd.DataFrame) -> str:
    """Structured summary for prompt injection (grounding without a second agent framework)."""
    lines = [
        f"Dataframe shape: {df.shape[0]} rows × {df.shape[1]} columns.",
        f"Column names: {', '.join(map(str, df.columns.tolist()))}.",
        f"dtypes:\n{df.dtypes.to_string()}",
        f"Missing values per column:\n{df.isna().sum().to_string()}",
        f"Sample (first 5 rows):\n{df.head(5).to_string()}",
    ]
    return "\n".join(lines)


def build_analysis_user_message(df: pd.DataFrame) -> str:
    return (
        "[User requested analysis of uploaded tabular data]\n\n"
        f"{describe_dataframe(df)}\n\n"
        "Summarize what this data contains and suggest sensible next analyses. "
        "Cite the row/column counts in your answer."
    )


def messages_for_ollama(state_messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build API message list: single system prompt + chat history."""
    out: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in state_messages:
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str):
            out.append({"role": role, "content": content})
    return out


# --- Ollama streaming ---


def _stream_line_tokens(chunk: dict) -> str:
    if "message" in chunk and isinstance(chunk["message"], dict):
        return chunk["message"].get("content") or ""
    return chunk.get("response", "") or ""


def stream_ollama_chat(model: str, messages: list[dict[str, str]], placeholder) -> str:
    """Stream tokens from Ollama /api/chat (multi-turn)."""
    full_response = ""
    res = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={"model": model, "messages": messages, "stream": True},
        stream=True,
        timeout=GENERATE_TIMEOUT,
    )
    res.raise_for_status()
    for line in res.iter_lines():
        if line:
            chunk = json.loads(line.decode("utf-8"))
            token = _stream_line_tokens(chunk)
            full_response += token
            placeholder.markdown(full_response + "▌")
    placeholder.markdown(full_response)
    return full_response


def conversation_transcript(state_messages: list[dict[str, Any]]) -> str:
    """Flatten history for /api/generate when chat API is disabled."""
    parts: list[str] = []
    for m in state_messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    return "\n\n".join(parts)


def stream_ollama_generate(model: str, prompt: str, placeholder) -> str:
    """Stream tokens from Ollama /api/generate (single-shot fallback)."""
    full_response = ""
    combined = f"{SYSTEM_PROMPT}\n\n{prompt}"
    res = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": model, "prompt": combined, "stream": True},
        stream=True,
        timeout=GENERATE_TIMEOUT,
    )
    res.raise_for_status()
    for line in res.iter_lines():
        if line:
            chunk = json.loads(line.decode("utf-8"))
            token = chunk.get("response", "")
            full_response += token
            placeholder.markdown(full_response + "▌")
    placeholder.markdown(full_response)
    return full_response


def run_model_stream(model: str, state_messages: list[dict[str, Any]], placeholder) -> str:
    if USE_CHAT_API:
        return stream_ollama_chat(model, messages_for_ollama(state_messages), placeholder)
    transcript = conversation_transcript(state_messages)
    return stream_ollama_generate(model, transcript, placeholder)


# 1. Page Configuration and Aesthetics
st.set_page_config(page_title="GOAT AI | Simon Business School", page_icon="🐐", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Welcome to GOAT AI. How can I assist your business decisions today?",
        }
    ]
if "ollama_pending_prompt" not in st.session_state:
    st.session_state.ollama_pending_prompt = None

# Injecting Simon Blue style CSS (main area stays light + dark text so Dark theme toggle does not hide chat)
st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa !important; color: #1a1a1a !important; }
    [data-testid="stSidebar"] { background-color: #002855; color: white; }
    .stButton>button { background-color: #FFCD00; color: #002855; border-radius: 5px; }
    section.main, section[data-testid="stMain"], [data-testid="stAppViewContainer"] > .main {
      color: #1a1a1a !important;
    }
    section.main [data-testid="stChatMessage"],
    section.main [data-testid="stChatMessage"] p,
    section.main [data-testid="stChatMessage"] span,
    section.main [data-testid="stMarkdownContainer"],
    section.main [data-testid="stMarkdownContainer"] p,
    section.main .stMarkdown,
    section.main h1, section.main h2, section.main h3,
    section.main [data-testid="stCaption"] {
      color: #1a1a1a !important;
    }
    [data-testid="stSidebar"] [data-testid="stImage"] img,
    [data-testid="stSidebar"] img {
      background: #ffffff !important;
      padding: 8px !important;
      border-radius: 6px !important;
      box-sizing: border-box !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def load_uploaded_dataframe(uploaded_file) -> Optional[pd.DataFrame]:
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        st.error(
            f"File is too large ({uploaded_file.size / (1024 * 1024):.1f} MB). "
            f"Maximum allowed is {MAX_UPLOAD_MB} MB."
        )
        logger.warning("Upload rejected: size %s exceeds limit", uploaded_file.size)
        return None
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        logger.exception("Failed to parse upload: %s", uploaded_file.name)
        st.error("Could not read this file. Please use a valid CSV or XLSX.")
        return None
    if len(df) > MAX_DATAFRAME_ROWS:
        st.error(
            f"Too many rows ({len(df):,}). Maximum allowed is {MAX_DATAFRAME_ROWS:,}. "
            "Try sampling or splitting your data."
        )
        logger.warning("Upload rejected: row count %s", len(df))
        return None
    return df


# 2. Sidebar: Configuration and Data Upload
selected_model = "llama3:latest"
with st.sidebar:
    if _SIMON_LOGO_SVG.is_file():
        st.image(str(_SIMON_LOGO_SVG), use_container_width=True)
    else:
        st.caption("Add logo: `static/urochester_simon_business_horizontal.svg` (local asset; no CDN).")

    st.title("Admin Console")
    st.caption(f"Ollama: `{OLLAMA_BASE_URL}`")
    st.caption(f"Upload limit: {MAX_UPLOAD_MB} MB · Max rows: {MAX_DATAFRAME_ROWS:,}")

    try:
        tags_res = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        tags_res.raise_for_status()
        models = [m["name"] for m in tags_res.json().get("models", [])]
        if not models:
            models = ["llama3:latest"]
        selected_model = st.selectbox("Active Brain (A100)", models)
    except Exception as e:
        logger.warning("Ollama tags failed: %s", e)
        st.warning("Could not reach Ollama. Check `OLLAMA_BASE_URL` and that `ollama serve` is running.")
        st.caption("Using default model name below if list is unavailable.")
        selected_model = st.text_input("Model name", value="llama3:latest")

    st.divider()

    st.subheader("Business Data Analysis")
    uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        df = load_uploaded_dataframe(uploaded_file)
        if df is not None:
            st.write("📊 Data Preview:", df.head(3))
            if st.button("Analyze with GOAT AI"):
                data_summary = build_analysis_user_message(df)
                st.session_state.messages.append({"role": "user", "content": data_summary})
                st.session_state.ollama_pending_prompt = True

# 3. Main Interface
st.title("🐐 GOAT AI - Strategic Intelligence")
st.caption("Running on high-performance A100 infrastructure at Simon Business School")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 3b. Complete pending analysis from sidebar (same request cycle as the button)
if st.session_state.ollama_pending_prompt:
    st.session_state.ollama_pending_prompt = None
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            full_response = run_model_stream(selected_model, st.session_state.messages, response_placeholder)
        except Exception as e:
            logger.exception("Ollama pending analysis failed")
            st.error(USER_FACING_ERROR)
            full_response = USER_FACING_ERROR
            response_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 4. Chat Input and Streaming Response
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            full_response = run_model_stream(selected_model, st.session_state.messages, response_placeholder)
        except Exception as e:
            logger.exception("Ollama chat failed")
            st.error(USER_FACING_ERROR)
            full_response = USER_FACING_ERROR
            response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
