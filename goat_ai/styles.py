"""Global Streamlit CSS (Simon branding + theme-safe chat/sidebar)."""

SIMON_APP_CSS = """
<style>
    /* ------------------------------------------------------------------ */
    /* Chat messages: follow Streamlit's own theme variable, not hardcoded */
    /* ------------------------------------------------------------------ */
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span,
    section.main [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
      color: var(--text-color, inherit) !important;
    }
    section.main h1, section.main h2, section.main h3,
    section.main [data-testid="stCaption"] {
      color: var(--text-color, inherit) !important;
    }

    /* ------------------------------------------------------------------ */
    /* Sidebar: always Simon navy regardless of app theme                  */
    /* ------------------------------------------------------------------ */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
      background-color: #003A70 !important;
      color: #ffffff !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    [data-testid="stSidebar"] [data-testid="stCaption"],
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
      color: #ffffff !important;
    }

    /* Logo white card */
    [data-testid="stSidebar"] [data-testid="stImage"] img,
    [data-testid="stSidebar"] img {
      background: #ffffff !important;
      padding: 8px !important;
      border-radius: 6px !important;
      box-sizing: border-box !important;
    }

    /* File uploader */
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

    /* ------------------------------------------------------------------ */
    /* Global button: Simon gold / navy                                    */
    /* ------------------------------------------------------------------ */
    .stButton > button {
      background-color: #FFCD00 !important;
      color: #003A70 !important;
      border: 2px solid #003A70 !important;
      border-radius: 6px !important;
      font-weight: 700 !important;
    }
    .stButton > button:hover {
      background-color: #e6b800 !important;
      color: #003A70 !important;
    }
    .stButton > button:active {
      background-color: #ccaa00 !important;
    }

    /* ------------------------------------------------------------------ */
    /* Sidebar buttons: explicit gold + navy + strong border               */
    /* (ensures visibility regardless of light/dark host theme)            */
    /* ------------------------------------------------------------------ */
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] button[kind="secondary"],
    [data-testid="stSidebar"] button[kind="primary"] {
      background-color: #FFCD00 !important;
      color: #003A70 !important;
      border: 2px solid #003A70 !important;
      border-radius: 6px !important;
      font-weight: 700 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
      background-color: #e6b800 !important;
      color: #003A70 !important;
    }

    /* Popover trigger inside sidebar */
    [data-testid="stSidebar"] [data-testid="stPopover"] > button,
    [data-testid="stSidebar"] button[aria-haspopup="dialog"] {
      background-color: #FFCD00 !important;
      color: #003A70 !important;
      border: 2px solid #003A70 !important;
      border-radius: 6px !important;
      font-weight: 700 !important;
    }

    /* Radio labels inside sidebar (theme switcher) */
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] span {
      color: #ffffff !important;
    }

    /* Sidebar links */
    [data-testid="stSidebar"] a {
      color: #FFCD00 !important;
      text-decoration: underline;
    }

    /* Header toolbar */
    [data-testid="stHeader"] [data-testid="stToolbar"] button {
      border: 1px solid rgba(255, 205, 0, 0.65) !important;
      border-radius: 8px !important;
    }
</style>
"""
