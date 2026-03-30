"""Global Streamlit CSS (Simon branding + theme-safe chat/sidebar)."""

SIMON_APP_CSS = """
<style>
    html[data-theme="light"] [data-testid="stAppViewContainer"] section.main {
      background-color: #f8f9fa !important;
    }

    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span,
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
      color: var(--st-text-color, #fafafa) !important;
    }
    section.main h1, section.main h2, section.main h3,
    section.main [data-testid="stCaption"] {
      color: var(--st-text-color, inherit) !important;
    }

    [data-testid="stSidebar"] {
      background-color: #003A70 !important;
      color: #ffffff !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    [data-testid="stSidebar"] [data-testid="stCaption"],
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
      color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stImage"] img,
    [data-testid="stSidebar"] img {
      background: #ffffff !important;
      padding: 8px !important;
      border-radius: 6px !important;
      box-sizing: border-box !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
      background-color: rgba(255, 255, 255, 0.18) !important;
      border: 1px solid rgba(255, 205, 0, 0.65) !important;
      color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
      color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
      color: #003A70 !important;
      background-color: #FFCD00 !important;
      border: none !important;
    }

    .stButton>button { background-color: #FFCD00 !important; color: #003A70 !important; border-radius: 5px !important; }

    /* Sidebar buttons (popover + st.button): force Simon gold / navy (fixes gray + white text) */
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] [data-testid="stPopover"] button,
    [data-testid="stSidebar"] button[aria-haspopup="dialog"] {
      background-color: #FFCD00 !important;
      color: #003A70 !important;
      border: 1px solid #003A70 !important;
      border-radius: 6px !important;
    }
    /* File uploader inner button */
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
      color: #002855 !important;
      background-color: #FFCD00 !important;
      border: none !important;
    }
    [data-testid="stSidebar"] a {
      color: #FFCD00 !important;
      text-decoration: underline;
    }

    [data-testid="stHeader"] [data-testid="stToolbar"] button {
      border: 1px solid rgba(255, 205, 0, 0.65) !important;
      border-radius: 8px !important;
    }
</style>
"""
