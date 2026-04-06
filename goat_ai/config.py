from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
APP_ROOT = _PACKAGE_ROOT.parent

_DEFAULT_SYSTEM_PROMPT = """You are GOAT AI, a helpful assistant for students and faculty at the University of Rochester Simon Business School.
You give clear, professional business-oriented analysis. Be precise and cite specific figures when data is available, but do not invent numbers or impose tabular structure on non-tabular topics.
Stay neutral, educational, and policy-safe: no harmful, discriminatory, or non-academic misuse of content.
If you are unsure, say so briefly."""

USER_FACING_ERROR = (
    "Sorry, the AI service is temporarily unavailable. Please try again or check that Ollama is running."
)


def _read_system_prompt() -> str:
    text = os.environ.get("GOAT_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT).strip()
    path = os.environ.get("GOAT_SYSTEM_PROMPT_FILE", "").strip()
    if path:
        p = Path(path)
        if p.is_file():
            text = p.read_text(encoding="utf-8").strip()
    return text


def _env_bool(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    """Runtime configuration (env-first; see docs/OPERATIONS.md)."""

    ollama_base_url: str
    generate_timeout: int
    max_upload_mb: int
    max_upload_bytes: int
    max_dataframe_rows: int
    use_chat_api: bool
    system_prompt: str
    app_root: Path
    logo_svg: Path
    log_db_path: Path
    gpu_target_uuid: str = ""
    gpu_target_index: int = 0

    @property
    def user_facing_error(self) -> str:
        return USER_FACING_ERROR


def load_settings() -> Settings:
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    max_mb = int(os.environ.get("GOAT_MAX_UPLOAD_MB", "20"))
    _default_log_db = str(APP_ROOT / "chat_logs.db")
    return Settings(
        ollama_base_url=base,
        generate_timeout=int(os.environ.get("OLLAMA_GENERATE_TIMEOUT", "120")),
        max_upload_mb=max_mb,
        max_upload_bytes=max_mb * 1024 * 1024,
        max_dataframe_rows=int(os.environ.get("GOAT_MAX_DATAFRAME_ROWS", "50000")),
        use_chat_api=_env_bool("GOAT_USE_CHAT_API", "true"),
        system_prompt=_read_system_prompt(),
        app_root=APP_ROOT,
        logo_svg=APP_ROOT / "static" / "urochester_simon_business_horizontal.svg",
        log_db_path=Path(os.environ.get("GOAT_LOG_PATH", _default_log_db)),
        gpu_target_uuid=os.environ.get("GOAT_GPU_UUID", "").strip(),
        gpu_target_index=int(os.environ.get("GOAT_GPU_INDEX", "0")),
    )
