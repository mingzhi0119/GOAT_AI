from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

_PACKAGE_ROOT = Path(__file__).resolve().parent
APP_ROOT = _PACKAGE_ROOT.parent
WORKSPACE_ROOT = APP_ROOT.parent
LOCAL_OLLAMA_INSTALL_DIR = WORKSPACE_ROOT / "ollama"
LOCAL_OLLAMA_RUNTIME_DIR = WORKSPACE_ROOT / "ollama-local"
LOCAL_OLLAMA_DEFAULT_URL = "http://127.0.0.1:11435"

ThemeStyleId = Literal["classic", "urochester", "thu"]

_DEFAULT_SYSTEM_PROMPTS: Final[dict[ThemeStyleId, str]] = {
    "classic": """You are GOAT AI, a helpful general-purpose assistant.
Give clear, accurate, well-structured answers across a wide range of topics. Be precise and practical, but do not invent facts, figures, or citations.
Stay neutral, educational, and policy-safe: no harmful, discriminatory, or non-academic misuse of content.
If you are unsure, say so briefly.""",
    "urochester": """You are GOAT AI, a helpful business-oriented assistant from the University of Rochester Simon Business School.
Favor clear, professional business analysis and decision support while staying useful on general questions. Be precise and cite specific figures when data is available, but do not invent numbers or impose tabular structure on non-tabular topics.
Stay neutral, educational, and policy-safe: no harmful, discriminatory, or non-academic misuse of content.
If you are unsure, say so briefly.""",
    "thu": """You are GOAT AI, a helpful research-oriented assistant from Tsinghua University.
Favor scientific, technical, and engineering rigor while remaining clear and practical on general questions. Explain assumptions, methods, and tradeoffs carefully, and do not invent facts, figures, or citations.
Stay neutral, educational, and policy-safe: no harmful, discriminatory, or non-academic misuse of content.
If you are unsure, say so briefly.""",
}
_DEFAULT_SYSTEM_PROMPT = _DEFAULT_SYSTEM_PROMPTS["classic"]

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


def default_system_prompt_for_theme(theme_style: ThemeStyleId) -> str:
    return _DEFAULT_SYSTEM_PROMPTS[theme_style]


def is_system_prompt_override_configured() -> bool:
    return bool(
        os.environ.get("GOAT_SYSTEM_PROMPT", "").strip()
        or os.environ.get("GOAT_SYSTEM_PROMPT_FILE", "").strip()
    )


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
    system_prompt_overridden: bool = False
    data_dir: Path = APP_ROOT / "data"
    api_key: str = ""
    api_key_write: str = ""
    api_credentials_json: str = ""
    require_session_owner: bool = False
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
    max_image_media_bytes: int = 12 * 1024 * 1024
    max_image_edge_px: int = 2048
    rag_rerank_mode: Literal["passthrough", "lexical"] = "passthrough"
    feature_code_sandbox_enabled: bool = False
    feature_agent_workbench_enabled: bool = False
    docker_socket_path: str = ""
    code_sandbox_default_image: str = "python:3.12-slim"
    code_sandbox_default_timeout_sec: int = 8
    code_sandbox_max_timeout_sec: int = 15
    code_sandbox_max_code_bytes: int = 32 * 1024
    code_sandbox_max_command_bytes: int = 8 * 1024
    code_sandbox_max_stdin_bytes: int = 16 * 1024
    code_sandbox_max_inline_files: int = 8
    code_sandbox_max_inline_file_bytes: int = 16 * 1024
    code_sandbox_max_output_bytes: int = 64 * 1024
    code_sandbox_cpu_limit: float = 0.5
    code_sandbox_memory_mb: int = 256
    # Safeguard (content moderation) configuration.
    # safeguard_enabled=False or safeguard_mode="off" → no safeguard, None injected downstream.
    safeguard_enabled: bool = True
    safeguard_mode: Literal["off", "input_only", "output_only", "full"] = "full"

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
    _max_image_media_bytes = int(
        os.environ.get("GOAT_MAX_IMAGE_MEDIA_BYTES", str(12 * 1024 * 1024))
    )
    _max_image_edge_px = int(os.environ.get("GOAT_MAX_IMAGE_EDGE_PX", "2048"))
    if _max_image_media_bytes < 1024:
        raise ValueError("GOAT_MAX_IMAGE_MEDIA_BYTES must be >= 1024")
    if _max_image_edge_px < 64:
        raise ValueError("GOAT_MAX_IMAGE_EDGE_PX must be >= 64")
    _rag_rerank = os.environ.get("GOAT_RAG_RERANK_MODE", "passthrough").strip().lower()
    if _rag_rerank not in ("passthrough", "lexical"):
        raise ValueError("GOAT_RAG_RERANK_MODE must be one of: passthrough, lexical")
    _feature_sandbox = _env_bool("GOAT_FEATURE_CODE_SANDBOX", "false")
    _feature_agent_workbench = _env_bool("GOAT_FEATURE_AGENT_WORKBENCH", "false")
    _docker_sock = os.environ.get("GOAT_DOCKER_SOCKET", "").strip()
    _sandbox_image = os.environ.get(
        "GOAT_CODE_SANDBOX_DEFAULT_IMAGE", "python:3.12-slim"
    ).strip()
    _sandbox_default_timeout = int(
        os.environ.get("GOAT_CODE_SANDBOX_DEFAULT_TIMEOUT_SEC", "8")
    )
    _sandbox_max_timeout = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_TIMEOUT_SEC", "15")
    )
    _sandbox_max_code_bytes = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_CODE_BYTES", str(32 * 1024))
    )
    _sandbox_max_command_bytes = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_COMMAND_BYTES", str(8 * 1024))
    )
    _sandbox_max_stdin_bytes = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_STDIN_BYTES", str(16 * 1024))
    )
    _sandbox_max_inline_files = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_INLINE_FILES", "8")
    )
    _sandbox_max_inline_file_bytes = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_INLINE_FILE_BYTES", str(16 * 1024))
    )
    _sandbox_max_output_bytes = int(
        os.environ.get("GOAT_CODE_SANDBOX_MAX_OUTPUT_BYTES", str(64 * 1024))
    )
    _sandbox_cpu_limit = float(os.environ.get("GOAT_CODE_SANDBOX_CPU_LIMIT", "0.5"))
    _sandbox_memory_mb = int(os.environ.get("GOAT_CODE_SANDBOX_MEMORY_MB", "256"))
    if not _sandbox_image:
        raise ValueError("GOAT_CODE_SANDBOX_DEFAULT_IMAGE must not be empty")
    if _sandbox_default_timeout < 1:
        raise ValueError("GOAT_CODE_SANDBOX_DEFAULT_TIMEOUT_SEC must be >= 1")
    if _sandbox_max_timeout < _sandbox_default_timeout:
        raise ValueError(
            "GOAT_CODE_SANDBOX_MAX_TIMEOUT_SEC must be >= GOAT_CODE_SANDBOX_DEFAULT_TIMEOUT_SEC"
        )
    if _sandbox_max_code_bytes < 256:
        raise ValueError("GOAT_CODE_SANDBOX_MAX_CODE_BYTES must be >= 256")
    if _sandbox_max_command_bytes < 64:
        raise ValueError("GOAT_CODE_SANDBOX_MAX_COMMAND_BYTES must be >= 64")
    if _sandbox_max_stdin_bytes < 0:
        raise ValueError("GOAT_CODE_SANDBOX_MAX_STDIN_BYTES must be >= 0")
    if _sandbox_max_inline_files < 0:
        raise ValueError("GOAT_CODE_SANDBOX_MAX_INLINE_FILES must be >= 0")
    if _sandbox_max_inline_file_bytes < 0:
        raise ValueError("GOAT_CODE_SANDBOX_MAX_INLINE_FILE_BYTES must be >= 0")
    if _sandbox_max_output_bytes < 1024:
        raise ValueError("GOAT_CODE_SANDBOX_MAX_OUTPUT_BYTES must be >= 1024")
    if _sandbox_cpu_limit <= 0:
        raise ValueError("GOAT_CODE_SANDBOX_CPU_LIMIT must be > 0")
    if _sandbox_memory_mb < 64:
        raise ValueError("GOAT_CODE_SANDBOX_MEMORY_MB must be >= 64")
    _safeguard_enabled = _env_bool("GOAT_SAFEGUARD_ENABLED", "true")
    _safeguard_mode = os.environ.get("GOAT_SAFEGUARD_MODE", "full").strip().lower()
    if _safeguard_mode not in ("off", "input_only", "output_only", "full"):
        raise ValueError(
            "GOAT_SAFEGUARD_MODE must be one of: off, input_only, output_only, full"
        )
    _api_key = os.environ.get("GOAT_API_KEY", "").strip()
    _api_key_write = os.environ.get("GOAT_API_KEY_WRITE", "").strip()
    _api_credentials_json = os.environ.get("GOAT_API_CREDENTIALS_JSON", "").strip()
    if _api_key_write and not _api_key:
        raise ValueError(
            "GOAT_API_KEY_WRITE requires GOAT_API_KEY (read key) to be set."
        )
    return Settings(
        ollama_base_url=base,
        generate_timeout=int(os.environ.get("OLLAMA_GENERATE_TIMEOUT", "120")),
        max_upload_mb=max_mb,
        max_upload_bytes=max_mb * 1024 * 1024,
        max_dataframe_rows=int(os.environ.get("GOAT_MAX_DATAFRAME_ROWS", "50000")),
        use_chat_api=_env_bool("GOAT_USE_CHAT_API", "true"),
        system_prompt=_read_system_prompt(),
        system_prompt_overridden=is_system_prompt_override_configured(),
        app_root=APP_ROOT,
        logo_svg=APP_ROOT / "static" / "urochester_simon_business_horizontal.svg",
        log_db_path=Path(os.environ.get("GOAT_LOG_PATH", _default_log_db)),
        data_dir=Path(os.environ.get("GOAT_DATA_DIR", _default_data_dir)),
        api_key=_api_key,
        api_key_write=_api_key_write,
        api_credentials_json=_api_credentials_json,
        require_session_owner=_env_bool("GOAT_REQUIRE_SESSION_OWNER", "false"),
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
        max_image_media_bytes=_max_image_media_bytes,
        max_image_edge_px=_max_image_edge_px,
        rag_rerank_mode=cast(Literal["passthrough", "lexical"], _rag_rerank),
        feature_code_sandbox_enabled=_feature_sandbox,
        feature_agent_workbench_enabled=_feature_agent_workbench,
        docker_socket_path=_docker_sock,
        code_sandbox_default_image=_sandbox_image,
        code_sandbox_default_timeout_sec=_sandbox_default_timeout,
        code_sandbox_max_timeout_sec=_sandbox_max_timeout,
        code_sandbox_max_code_bytes=_sandbox_max_code_bytes,
        code_sandbox_max_command_bytes=_sandbox_max_command_bytes,
        code_sandbox_max_stdin_bytes=_sandbox_max_stdin_bytes,
        code_sandbox_max_inline_files=_sandbox_max_inline_files,
        code_sandbox_max_inline_file_bytes=_sandbox_max_inline_file_bytes,
        code_sandbox_max_output_bytes=_sandbox_max_output_bytes,
        code_sandbox_cpu_limit=_sandbox_cpu_limit,
        code_sandbox_memory_mb=_sandbox_memory_mb,
        safeguard_enabled=_safeguard_enabled,
        safeguard_mode=cast(
            Literal["off", "input_only", "output_only", "full"], _safeguard_mode
        ),
    )
