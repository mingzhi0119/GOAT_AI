from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_PACKAGE_ROOT = Path(__file__).resolve().parent
APP_ROOT = _PACKAGE_ROOT.parent
WORKSPACE_ROOT = APP_ROOT.parent
LOCAL_OLLAMA_INSTALL_DIR = WORKSPACE_ROOT / "ollama"
LOCAL_OLLAMA_RUNTIME_DIR = WORKSPACE_ROOT / "ollama-local"
LOCAL_OLLAMA_DEFAULT_URL = "http://127.0.0.1:11435"

_DEFAULT_SYSTEM_PROMPT = """You are GOAT AI, a helpful assistant for students and faculty at the University of Rochester Simon Business School.
You give clear, professional business-oriented analysis. Be precise and cite specific figures when data is available, but do not invent numbers or impose tabular structure on non-tabular topics.
Stay neutral, educational, and policy-safe: no harmful, discriminatory, or non-academic misuse of content.
If you are unsure, say so briefly."""

USER_FACING_ERROR = "Sorry, the AI service is temporarily unavailable. Please try again or check that Ollama is running."
_DOTENV_QUOTES: Final[tuple[str, str]] = ("'", '"')


def _strip_wrapped_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in _DOTENV_QUOTES:
        return value[1:-1]
    return value


def load_dotenv_if_present() -> None:
    """Load ``APP_ROOT/.env`` when present (idempotent for keys already in the environment)."""
    _load_dotenv_file(APP_ROOT / ".env")


def _load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        env_name = key.strip()
        if not env_name or env_name in os.environ:
            continue

        os.environ[env_name] = _strip_wrapped_quotes(raw_value.strip())


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


def _has_local_ollama_layout() -> bool:
    install_bin = LOCAL_OLLAMA_INSTALL_DIR / "bin" / "ollama"
    runtime_dir = LOCAL_OLLAMA_RUNTIME_DIR
    return install_bin.is_file() and runtime_dir.is_dir()


def _default_ollama_base_url() -> str:
    if _has_local_ollama_layout():
        return LOCAL_OLLAMA_DEFAULT_URL
    return "http://127.0.0.1:11434"


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
    data_dir: Path = APP_ROOT / "data"
    api_key: str = ""
    rate_limit_window_sec: int = 60
    rate_limit_max_requests: int = 60
    deploy_target: str = "auto"
    server_port: int = 62606
    local_port: int = 62606
    gpu_target_uuid: str = ""
    gpu_target_index: int = 0
    latency_rolling_max_samples: int = 20
    model_cap_cache_ttl_sec: int = 60
    ready_skip_ollama_probe: bool = False
    ollama_read_retry_attempts: int = 3
    ollama_read_retry_base_ms: int = 120
    ollama_read_retry_jitter_ms: int = 80
    ollama_circuit_breaker_failures: int = 3
    ollama_circuit_breaker_open_sec: int = 20
    idempotency_ttl_sec: int = 300
    max_chat_messages: int = 120
    max_chat_payload_bytes: int = 512000
    chat_first_event_timeout_sec: int = 90

    @property
    def user_facing_error(self) -> str:
        return USER_FACING_ERROR


def load_settings() -> Settings:
    _load_dotenv_file(APP_ROOT / ".env")
    base = os.environ.get("OLLAMA_BASE_URL", _default_ollama_base_url()).rstrip("/")
    max_mb = int(os.environ.get("GOAT_MAX_UPLOAD_MB", "20"))
    _default_log_db = str(APP_ROOT / "chat_logs.db")
    _default_data_dir = str(APP_ROOT / "data")
    _rate_limit_window_sec = int(os.environ.get("GOAT_RATE_LIMIT_WINDOW_SEC", "60"))
    _rate_limit_max_requests = int(os.environ.get("GOAT_RATE_LIMIT_MAX_REQUESTS", "60"))
    _deploy_target = os.environ.get("GOAT_DEPLOY_TARGET", "auto").strip().lower()
    _server_port = int(os.environ.get("GOAT_SERVER_PORT", "62606"))
    _local_port = int(os.environ.get("GOAT_LOCAL_PORT", str(_server_port)))
    _lat_n = int(os.environ.get("GOAT_LATENCY_ROLLING_MAX_SAMPLES", "20"))
    _cap_ttl = int(os.environ.get("GOAT_MODEL_CAP_CACHE_TTL_SEC", "60"))
    _read_retry_attempts = int(os.environ.get("GOAT_OLLAMA_READ_RETRY_ATTEMPTS", "3"))
    _read_retry_base_ms = int(os.environ.get("GOAT_OLLAMA_READ_RETRY_BASE_MS", "120"))
    _read_retry_jitter_ms = int(
        os.environ.get("GOAT_OLLAMA_READ_RETRY_JITTER_MS", "80")
    )
    _breaker_failures = int(os.environ.get("GOAT_OLLAMA_CIRCUIT_BREAKER_FAILURES", "3"))
    _breaker_open_sec = int(
        os.environ.get("GOAT_OLLAMA_CIRCUIT_BREAKER_OPEN_SEC", "20")
    )
    _idempotency_ttl_sec = int(os.environ.get("GOAT_IDEMPOTENCY_TTL_SEC", "300"))
    _max_chat_messages = int(os.environ.get("GOAT_MAX_CHAT_MESSAGES", "120"))
    _max_chat_payload_bytes = int(
        os.environ.get("GOAT_MAX_CHAT_PAYLOAD_BYTES", "512000")
    )
    _chat_first_event_timeout_sec = int(
        os.environ.get("OLLAMA_CHAT_FIRST_EVENT_TIMEOUT", "90")
    )
    if _deploy_target not in {"auto", "server", "local"}:
        raise ValueError("GOAT_DEPLOY_TARGET must be one of: auto, server, local")
    if _rate_limit_window_sec < 1:
        raise ValueError("GOAT_RATE_LIMIT_WINDOW_SEC must be >= 1")
    if _rate_limit_max_requests < 1:
        raise ValueError("GOAT_RATE_LIMIT_MAX_REQUESTS must be >= 1")
    if _server_port < 1 or _server_port > 65535:
        raise ValueError("GOAT_SERVER_PORT must be between 1 and 65535")
    if _local_port < 1 or _local_port > 65535:
        raise ValueError("GOAT_LOCAL_PORT must be between 1 and 65535")
    if _lat_n < 1:
        raise ValueError("GOAT_LATENCY_ROLLING_MAX_SAMPLES must be >= 1")
    if _cap_ttl < 0:
        raise ValueError("GOAT_MODEL_CAP_CACHE_TTL_SEC must be >= 0")
    if _read_retry_attempts < 1:
        raise ValueError("GOAT_OLLAMA_READ_RETRY_ATTEMPTS must be >= 1")
    if _read_retry_base_ms < 0:
        raise ValueError("GOAT_OLLAMA_READ_RETRY_BASE_MS must be >= 0")
    if _read_retry_jitter_ms < 0:
        raise ValueError("GOAT_OLLAMA_READ_RETRY_JITTER_MS must be >= 0")
    if _breaker_failures < 1:
        raise ValueError("GOAT_OLLAMA_CIRCUIT_BREAKER_FAILURES must be >= 1")
    if _breaker_open_sec < 1:
        raise ValueError("GOAT_OLLAMA_CIRCUIT_BREAKER_OPEN_SEC must be >= 1")
    if _idempotency_ttl_sec < 1:
        raise ValueError("GOAT_IDEMPOTENCY_TTL_SEC must be >= 1")
    if _max_chat_messages < 1:
        raise ValueError("GOAT_MAX_CHAT_MESSAGES must be >= 1")
    if _max_chat_payload_bytes < 1024:
        raise ValueError("GOAT_MAX_CHAT_PAYLOAD_BYTES must be >= 1024")
    if _chat_first_event_timeout_sec < 1:
        raise ValueError("OLLAMA_CHAT_FIRST_EVENT_TIMEOUT must be >= 1")
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
        data_dir=Path(os.environ.get("GOAT_DATA_DIR", _default_data_dir)),
        api_key=os.environ.get("GOAT_API_KEY", "").strip(),
        rate_limit_window_sec=_rate_limit_window_sec,
        rate_limit_max_requests=_rate_limit_max_requests,
        deploy_target=_deploy_target,
        server_port=_server_port,
        local_port=_local_port,
        gpu_target_uuid=os.environ.get("GOAT_GPU_UUID", "").strip(),
        gpu_target_index=int(os.environ.get("GOAT_GPU_INDEX", "0")),
        latency_rolling_max_samples=_lat_n,
        model_cap_cache_ttl_sec=_cap_ttl,
        ready_skip_ollama_probe=_env_bool("GOAT_READY_SKIP_OLLAMA_PROBE", "false"),
        ollama_read_retry_attempts=_read_retry_attempts,
        ollama_read_retry_base_ms=_read_retry_base_ms,
        ollama_read_retry_jitter_ms=_read_retry_jitter_ms,
        ollama_circuit_breaker_failures=_breaker_failures,
        ollama_circuit_breaker_open_sec=_breaker_open_sec,
        idempotency_ttl_sec=_idempotency_ttl_sec,
        max_chat_messages=_max_chat_messages,
        max_chat_payload_bytes=_max_chat_payload_bytes,
        chat_first_event_timeout_sec=_chat_first_event_timeout_sec,
    )
