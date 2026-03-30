import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
GENERATE_TIMEOUT = int(os.environ.get("OLLAMA_GENERATE_TIMEOUT", "120"))

_APP_DIR = Path(__file__).resolve().parent
_SIMON_LOGO_SVG = _APP_DIR / "static" / "urochester_simon_business_horizontal.svg"


def stream_ollama_generate(model: str, prompt: str, placeholder) -> str:
    """Stream tokens from Ollama /api/generate into placeholder; return full text."""
    full_response = ""
    res = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": True},
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


# 1. Page Configuration and Aesthetics
st.set_page_config(page_title="GOAT AI | Simon Business School", page_icon="🐐", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to GOAT AI. How can I assist your business decisions today?"}
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
    /* Chat + markdown in main: force readable text when Streamlit theme is Dark */
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
    /* Sidebar logo: light backing so navy SVG reads on Simon blue */
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

# 2. Sidebar: Configuration and Data Upload
selected_model = "llama3:latest"
with st.sidebar:
    if _SIMON_LOGO_SVG.is_file():
        st.image(str(_SIMON_LOGO_SVG), use_container_width=True)
    else:
        st.image(
            "https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/University_of_Rochester_Simon_Business_School_logo.png/250px-University_of_Rochester_Simon_Business_School_logo.png"
        )
    st.title("Admin Console")
    st.caption(f"Ollama: `{OLLAMA_BASE_URL}`")

    try:
        tags_res = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        tags_res.raise_for_status()
        models = [m["name"] for m in tags_res.json().get("models", [])]
        if not models:
            models = ["llama3:latest"]
        selected_model = st.selectbox("Active Brain (A100)", models)
    except Exception as e:
        st.warning(f"Could not reach Ollama at {OLLAMA_BASE_URL}: {e}")
        st.caption("Using default model name; ensure `ollama serve` is running and the model is pulled.")
        selected_model = st.text_input("Model name", value="llama3:latest")

    st.divider()

    st.subheader("Business Data Analysis")
    uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df = (
                pd.read_csv(uploaded_file)
                if uploaded_file.name.lower().endswith(".csv")
                else pd.read_excel(uploaded_file)
            )
        except Exception as e:
            st.error(f"Could not read file: {e}")
            df = None
        if df is not None:
            st.write("📊 Data Preview:", df.head(3))
            if st.button("Analyze with GOAT AI"):
                data_summary = (
                    f"I have a dataset with {df.shape[0]} rows and {df.shape[1]} columns. "
                    f"Here is the head:\n{df.head(2).to_string()}\nPlease summarize and suggest next analyses."
                )
                st.session_state.messages.append({"role": "user", "content": data_summary})
                st.session_state.ollama_pending_prompt = data_summary

# 3. Main Interface
st.title("🐐 GOAT AI - Strategic Intelligence")
st.caption("Running on high-performance A100 infrastructure at Simon Business School")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 3b. Complete pending analysis from sidebar (same request cycle as the button)
pending = st.session_state.ollama_pending_prompt
if pending:
    st.session_state.ollama_pending_prompt = None
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            full_response = stream_ollama_generate(selected_model, pending, response_placeholder)
        except Exception as e:
            st.error(f"Error connecting to AI: {e}")
            full_response = "Sorry, I'm experiencing some latency on the A100 node."
            response_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 4. Chat Input and Streaming Response
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            full_response = stream_ollama_generate(selected_model, prompt, response_placeholder)
        except Exception as e:
            st.error(f"Error connecting to AI: {e}")
            full_response = "Sorry, I'm experiencing some latency on the A100 node."
            response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
