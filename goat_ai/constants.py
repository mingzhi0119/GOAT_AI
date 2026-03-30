"""Centralized session keys and copy — avoids magic strings scattered in the UI layer."""

# streamlit.session_state keys (single source of truth)
SESSION_MESSAGES = "messages"
SESSION_PENDING_ANALYSIS = "ollama_pending_prompt"

WELCOME_ASSISTANT = "Welcome to GOAT AI. How can I assist your business decisions today?"
