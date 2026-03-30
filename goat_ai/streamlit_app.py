from __future__ import annotations

import logging

import streamlit as st

from goat_ai.config import USER_FACING_ERROR, Settings, load_settings
from goat_ai.constants import (
    SESSION_MESSAGES,
    SESSION_PENDING_ANALYSIS,
    WELCOME_ASSISTANT,
)
from goat_ai.ollama_client import OllamaService
from goat_ai.styles import SIMON_APP_CSS
from goat_ai.theme_controls import render_theme_switcher
from goat_ai.tools import build_analysis_user_message
from goat_ai.uploads import load_tabular_upload

logger = logging.getLogger(__name__)


def _init_session_state() -> None:
    if SESSION_MESSAGES not in st.session_state:
        st.session_state[SESSION_MESSAGES] = [{"role": "assistant", "content": WELCOME_ASSISTANT}]
    if SESSION_PENDING_ANALYSIS not in st.session_state:
        st.session_state[SESSION_PENDING_ANALYSIS] = None


def _inject_styles() -> None:
    st.markdown(SIMON_APP_CSS, unsafe_allow_html=True)


def _stream_assistant_turn(ollama: OllamaService, model: str, *, failure_log: str) -> str:
    """Render one assistant message with streaming; returns full text (or user-facing error string)."""
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            return ollama.stream_from_session(model, st.session_state[SESSION_MESSAGES], response_placeholder)
        except Exception:
            logger.exception(failure_log)
            st.error(USER_FACING_ERROR)
            text = USER_FACING_ERROR
            response_placeholder.markdown(text)
            return text


def _render_sidebar(settings: Settings, ollama: OllamaService) -> str:
    """Sidebar UI; returns selected model name."""
    selected_model = "llama3:latest"
    with st.sidebar:
        if settings.logo_svg.is_file():
            st.image(str(settings.logo_svg), use_container_width=True)
        else:
            st.caption("Add logo: `static/urochester_simon_business_horizontal.svg` (local asset; no CDN).")

        with st.popover("🎨 Theme & display", use_container_width=True):
            render_theme_switcher()
        r1, r2 = st.columns(2)
        with r1:
            if st.button("🔄 Refresh", use_container_width=True, key="sb_refresh", help="Re-run the app script"):
                st.rerun()
        with r2:
            if st.button("🗑️ Clear chat", use_container_width=True, key="sb_clear", help="Reset conversation"):
                st.session_state[SESSION_MESSAGES] = [{"role": "assistant", "content": WELCOME_ASSISTANT}]
                st.session_state[SESSION_PENDING_ANALYSIS] = None
                st.rerun()

        st.caption(f"Upload limit: {settings.max_upload_mb} MB · Max rows: {settings.max_dataframe_rows:,}")

        try:
            models = ollama.list_model_names()
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
            result = load_tabular_upload(uploaded_file, settings)
            if result.user_error:
                st.error(result.user_error)
            elif result.dataframe is not None:
                df = result.dataframe
                st.write("📊 Data Preview:", df.head(3))
                if st.button("Analyze with GOAT AI"):
                    st.session_state[SESSION_MESSAGES].append(
                        {"role": "user", "content": build_analysis_user_message(df)}
                    )
                    st.session_state[SESSION_PENDING_ANALYSIS] = True

    return selected_model


def _run_pending_analysis(ollama: OllamaService, model: str) -> None:
    if not st.session_state[SESSION_PENDING_ANALYSIS]:
        return
    st.session_state[SESSION_PENDING_ANALYSIS] = None
    full_response = _stream_assistant_turn(ollama, model, failure_log="Ollama pending analysis failed")
    st.session_state[SESSION_MESSAGES].append({"role": "assistant", "content": full_response})


def _run_chat_input(ollama: OllamaService, model: str) -> None:
    if not (prompt := st.chat_input()):
        return
    st.session_state[SESSION_MESSAGES].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    full_response = _stream_assistant_turn(ollama, model, failure_log="Ollama chat failed")
    st.session_state[SESSION_MESSAGES].append({"role": "assistant", "content": full_response})


def run() -> None:
    """Streamlit entry: page config, state, layout, Ollama-backed chat."""
    st.set_page_config(page_title="GOAT AI | Simon Business School", page_icon="🐐", layout="wide")
    settings = load_settings()
    ollama = OllamaService(settings)
    _init_session_state()
    _inject_styles()

    selected_model = _render_sidebar(settings, ollama)

    st.title("🐐 GOAT AI - Strategic Intelligence")
    st.caption("Running on high-performance A100 infrastructure at Simon Business School")

    for msg in st.session_state[SESSION_MESSAGES]:
        st.chat_message(msg["role"]).write(msg["content"])

    _run_pending_analysis(ollama, selected_model)
    _run_chat_input(ollama, selected_model)
