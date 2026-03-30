"""GOAT AI — Streamlit entrypoint. Logic lives in the `goat_ai` package."""

from goat_ai.logging_config import configure_logging
from goat_ai.streamlit_app import run

configure_logging()
run()
