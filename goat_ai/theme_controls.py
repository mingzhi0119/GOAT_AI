"""In-app theme switcher: session-state radio + CSS injection (no fragile iframe/localStorage)."""

from __future__ import annotations

import streamlit as st

from goat_ai.constants import SESSION_THEME

_LIGHT_OVERRIDES = """
<style>
/* ---- Light theme: force bright main area ---- */
[data-testid="stAppViewContainer"] > section.main,
[data-testid="stMain"] { background-color: #f8f9fa !important; }

section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span,
section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
  color: #1a1a2e !important;
}
section.main h1, section.main h2, section.main h3,
section.main [data-testid="stCaption"] { color: #1a1a2e !important; }
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] div { color: #1a1a2e !important; }

/* Selectbox / text-input text in main area */
section.main .stSelectbox div[data-baseweb] span,
section.main .stTextInput input { color: #1a1a2e !important; }
</style>
"""

_DARK_OVERRIDES = """
<style>
/* ---- Dark theme: force dark main area ---- */
[data-testid="stAppViewContainer"] > section.main,
[data-testid="stMain"] { background-color: #0e1117 !important; }

section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span,
section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
  color: #fafafa !important;
}
section.main h1, section.main h2, section.main h3,
section.main [data-testid="stCaption"] { color: #fafafa !important; }
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] div { color: #fafafa !important; }
</style>
"""


def render_theme_switcher() -> None:
    """Render Light / Dark / System selector bound directly to session state."""
    st.caption("Display theme")
    st.radio(
        "Theme",
        options=["System", "Light", "Dark"],
        key=SESSION_THEME,
        horizontal=True,
        label_visibility="collapsed",
    )


def get_theme_css() -> str:
    """Return CSS overrides for the currently selected theme."""
    theme = st.session_state.get(SESSION_THEME, "System")
    if theme == "Light":
        return _LIGHT_OVERRIDES
    if theme == "Dark":
        return _DARK_OVERRIDES
    return ""
