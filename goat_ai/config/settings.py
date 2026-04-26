from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from goat_ai.shared.workbench_connector_bindings import (
    parse_workbench_connector_bindings_json,
)

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = _PACKAGE_ROOT.parent
DEFAULT_RUNTIME_ROOT = APP_ROOT / "var"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
SCHOOL_OLLAMA_LOCAL_URL = "http://127.0.0.1:11435"
SCHOOL_OLLAMA_PROFILE = "school-ubuntu"

ThemeStyleId = Literal["classic", "urochester", "thu"]
CodeSandboxProviderId = Literal["docker", "localhost"]
WorkbenchWebProviderId = Literal["disabled", "duckduckgo"]
ObjectStoreBackendId = Literal["local", "s3"]
ObjectStoreS3AddressingStyle = Literal["auto", "path", "virtual"]
RuntimeMetadataBackendId = Literal["sqlite", "postgres"]
DeployMode = Literal[0, 1, 2]
DeployModeName = Literal["local", "school_server", "remote"]

LOCAL_DEPLOY_MODE = 0
SCHOOL_SERVER_DEPLOY_MODE = 1
REMOTE_DEPLOY_MODE = 2

_DEPLOY_MODE_NAMES: Final[dict[int, DeployModeName]] = {
    LOCAL_DEPLOY_MODE: "local",
    SCHOOL_SERVER_DEPLOY_MODE: "school_server",
    REMOTE_DEPLOY_MODE: "remote",
}
_AUTH_CONFIG_ENV_NAMES: Final[tuple[str, ...]] = (
    "GOAT_API_KEY",
    "GOAT_API_KEY_WRITE",
    "GOAT_API_CREDENTIALS_JSON",
    "GOAT_SHARED_ACCESS_PASSWORD",
    "GOAT_SHARED_ACCESS_PASSWORD_HASH",
    "GOAT_SHARED_ACCESS_SESSION_SECRET",
    "GOAT_SHARED_ACCESS_SESSION_TTL_SEC",
    "GOAT_ACCOUNT_AUTH_ENABLED",
    "GOAT_BROWSER_SESSION_SECRET",
    "GOAT_ACCOUNT_SESSION_TTL_SEC",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "GOAT_GOOGLE_OAUTH_STATE_TTL_SEC",
    "GOAT_REQUIRE_SESSION_OWNER",
)
_REMOVED_AUTH_CONFIG_MESSAGE = (
    "Auth configuration has been removed for GOAT AI demo deployments; "
    "remove {names} from the current environment."
)
_DEFAULT_REMOTE_RATE_LIMIT_MAX_REQUESTS: Final[int] = 20
_DEFAULT_NON_REMOTE_RATE_LIMIT_MAX_REQUESTS: Final[int] = 60

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
_LEGACY_RUNTIME_COPY_NAMES: Final[tuple[str, ...]] = (
    "chat_logs.db",
    "chat_logs.db-shm",
    "chat_logs.db-wal",
)
_LEGACY_RUNTIME_COPY_DIRS: Final[tuple[str, ...]] = ("data", "logs")


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


def deploy_mode_name(value: int) -> DeployModeName:
    try:
        return _DEPLOY_MODE_NAMES[value]
    except KeyError as exc:  # pragma: no cover - load_settings validates first
        raise ValueError("GOAT_DEPLOY_MODE must be one of: 0, 1, 2") from exc


def default_system_prompt_for_theme(theme_style: ThemeStyleId) -> str:
    return _DEFAULT_SYSTEM_PROMPTS[theme_style]


def is_system_prompt_override_configured() -> bool:
    return bool(
        os.environ.get("GOAT_SYSTEM_PROMPT", "").strip()
        or os.environ.get("GOAT_SYSTEM_PROMPT_FILE", "").strip()
    )


def _env_bool(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def _school_ollama_local_enabled() -> bool:
    if _env_bool("GOAT_USE_SCHOOL_OLLAMA_LOCAL", "false"):
        return True
    profile = os.environ.get("GOAT_OLLAMA_PROFILE", "").strip().lower()
    return profile == SCHOOL_OLLAMA_PROFILE


def _default_ollama_base_url() -> str:
    if _school_ollama_local_enabled():
        return SCHOOL_OLLAMA_LOCAL_URL
    return DEFAULT_OLLAMA_BASE_URL


def _validate_pwdlib_hash(value: str) -> None:
    candidate = value.strip()
    if not candidate:
        return

    from pwdlib import PasswordHash

    try:
        PasswordHash.recommended().verify("goat-password-config-probe", candidate)
    except Exception as exc:  # pragma: no cover - exercised via config tests
        raise ValueError(
            "GOAT_SHARED_ACCESS_PASSWORD_HASH must be a valid pwdlib hash."
        ) from exc


def _resolve_env_path(value: str, *, relative_to: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (relative_to / path).resolve()


def _resolve_runtime_root() -> tuple[Path, bool]:
    configured = os.environ.get("GOAT_RUNTIME_ROOT", "").strip()
    if configured:
        return _resolve_env_path(configured, relative_to=APP_ROOT), True
    return DEFAULT_RUNTIME_ROOT, False


def _verify_copied_path(source: Path, target: Path) -> None:
    if source.is_dir():
        if not target.is_dir():
            raise RuntimeError(f"Expected migrated directory at {target}")
        for nested_source in source.rglob("*"):
            relative = nested_source.relative_to(source)
            nested_target = target / relative
            if nested_source.is_dir():
                if not nested_target.is_dir():
                    raise RuntimeError(f"Missing migrated directory {nested_target}")
                continue
            if not nested_target.is_file():
                raise RuntimeError(f"Missing migrated file {nested_target}")
            if nested_source.stat().st_size != nested_target.stat().st_size:
                raise RuntimeError(f"Migrated file size mismatch for {nested_target}")
        return

    if not target.is_file():
        raise RuntimeError(f"Expected migrated file at {target}")
    if source.stat().st_size != target.stat().st_size:
        raise RuntimeError(f"Migrated file size mismatch for {target}")


def _copy_legacy_runtime_path(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    _verify_copied_path(source, target)


def _migrate_legacy_runtime_state(runtime_root: Path) -> None:
    if runtime_root.exists():
        return

    legacy_pairs: list[tuple[Path, Path]] = []
    for name in _LEGACY_RUNTIME_COPY_NAMES:
        legacy_source = APP_ROOT / name
        if legacy_source.exists():
            legacy_pairs.append((legacy_source, runtime_root / name))
    for name in _LEGACY_RUNTIME_COPY_DIRS:
        legacy_source = APP_ROOT / name
        if legacy_source.exists():
            legacy_pairs.append((legacy_source, runtime_root / name))

    if not legacy_pairs:
        return

    runtime_root_created = False
    try:
        runtime_root.mkdir(parents=True, exist_ok=False)
        runtime_root_created = True
        for source, target in legacy_pairs:
            _copy_legacy_runtime_path(source, target)
    except Exception as exc:  # pragma: no cover - exercised via tests
        if runtime_root_created and runtime_root.exists():
            shutil.rmtree(runtime_root, ignore_errors=True)
        raise RuntimeError(
            "Failed to migrate legacy runtime state into GOAT_RUNTIME_ROOT."
        ) from exc


def _ensure_directory(path: Path, *, label: str) -> Path:
    if path.exists() and not path.is_dir():
        raise ValueError(f"{label} must point to a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration (env-first; see docs/operations/OPERATIONS.md)."""

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
    runtime_root: Path = DEFAULT_RUNTIME_ROOT
    log_dir: Path = DEFAULT_RUNTIME_ROOT / "logs"
    system_prompt_overridden: bool = False
    data_dir: Path = DEFAULT_RUNTIME_ROOT / "data"
    runtime_metadata_backend: RuntimeMetadataBackendId = "sqlite"
    runtime_postgres_dsn: str = ""
    object_store_backend: ObjectStoreBackendId = "local"
    object_store_root: Path = DEFAULT_RUNTIME_ROOT / "data"
    object_store_bucket: str = ""
    object_store_prefix: str = ""
    object_store_endpoint_url: str = ""
    object_store_region: str = ""
    object_store_access_key_id: str = ""
    object_store_secret_access_key: str = ""
    object_store_s3_addressing_style: ObjectStoreS3AddressingStyle = "auto"
    api_key: str = ""
    api_key_write: str = ""
    api_credentials_json: str = ""
    account_auth_enabled: bool = False
    browser_session_secret: str = ""
    account_session_ttl_sec: int = 60 * 60 * 24 * 30
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    google_oauth_state_ttl_sec: int = 60 * 10
    shared_access_password: str = ""
    shared_access_password_hash: str = ""
    shared_access_session_secret: str = ""
    shared_access_session_ttl_sec: int = 60 * 60 * 24 * 30
    require_session_owner: bool = False
    rate_limit_window_sec: int = 60
    rate_limit_max_requests: int = 60
    ollama_max_concurrent_requests: int = 2
    deploy_mode: DeployMode = LOCAL_DEPLOY_MODE
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
    code_sandbox_provider: CodeSandboxProviderId = "docker"
    workbench_web_provider: WorkbenchWebProviderId = "duckduckgo"
    workbench_web_max_results: int = 6
    workbench_web_timeout_sec: int = 15
    workbench_web_region: str = "wt-wt"
    workbench_web_safesearch: Literal["on", "moderate", "off"] = "moderate"
    workbench_langgraph_enabled: bool = True
    workbench_browse_max_steps: int = 2
    workbench_deep_research_max_steps: int = 3
    workbench_connector_bindings_json: str = ""
    docker_socket_path: str = ""
    code_sandbox_default_image: str = "python:3.12-slim"
    code_sandbox_localhost_shell: str = ""
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

    @property
    def shared_access_enabled(self) -> bool:
        return bool(
            self.shared_access_password_hash.strip()
            or self.shared_access_password.strip()
        )

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(
            self.google_client_id.strip()
            and self.google_client_secret.strip()
            and self.google_redirect_uri.strip()
        )

    @property
    def browser_auth_required(self) -> bool:
        return self.shared_access_enabled or self.account_auth_enabled

    @property
    def deploy_mode_name(self) -> DeployModeName:
        return deploy_mode_name(self.deploy_mode)

    @property
    def is_remote_deploy(self) -> bool:
        return self.deploy_mode == REMOTE_DEPLOY_MODE


def resolve_localhost_sandbox_shell(settings: Settings) -> str | None:
    configured = settings.code_sandbox_localhost_shell.strip()
    if configured:
        return shutil.which(configured) or (
            configured if Path(configured).is_file() else None
        )
    if os.name == "nt":
        return shutil.which("pwsh.exe") or shutil.which("powershell.exe")
    return shutil.which("sh") or ("/bin/sh" if Path("/bin/sh").is_file() else None)


def load_settings() -> Settings:
    _load_dotenv_file(APP_ROOT / ".env")
    base = os.environ.get("OLLAMA_BASE_URL", _default_ollama_base_url()).rstrip("/")
    max_mb = int(os.environ.get("GOAT_MAX_UPLOAD_MB", "20"))
    runtime_root, runtime_root_explicit = _resolve_runtime_root()
    if not runtime_root_explicit:
        _migrate_legacy_runtime_state(runtime_root)
    runtime_root = _ensure_directory(runtime_root, label="GOAT_RUNTIME_ROOT")
    _default_log_db = runtime_root / "chat_logs.db"
    _default_data_dir = runtime_root / "data"
    _default_log_dir = runtime_root / "logs"
    _legacy_deploy_target = os.environ.get("GOAT_DEPLOY_TARGET", "").strip()
    if _legacy_deploy_target:
        raise ValueError(
            "GOAT_DEPLOY_TARGET is no longer supported; use GOAT_DEPLOY_MODE=0|1|2."
        )
    _deploy_mode_raw = os.environ.get("GOAT_DEPLOY_MODE", "").strip()
    if not _deploy_mode_raw:
        raise ValueError("GOAT_DEPLOY_MODE is required and must be one of: 0, 1, 2")
    try:
        _deploy_mode = int(_deploy_mode_raw)
    except ValueError as exc:
        raise ValueError("GOAT_DEPLOY_MODE must be one of: 0, 1, 2") from exc
    deploy_mode_name(_deploy_mode)
    configured_auth_envs = [
        name for name in _AUTH_CONFIG_ENV_NAMES if os.environ.get(name, "").strip()
    ]
    if configured_auth_envs:
        raise ValueError(
            _REMOVED_AUTH_CONFIG_MESSAGE.format(names=", ".join(configured_auth_envs))
        )
    _default_rate_limit_max_requests = (
        _DEFAULT_REMOTE_RATE_LIMIT_MAX_REQUESTS
        if _deploy_mode == REMOTE_DEPLOY_MODE
        else _DEFAULT_NON_REMOTE_RATE_LIMIT_MAX_REQUESTS
    )
    _rate_limit_window_sec = int(os.environ.get("GOAT_RATE_LIMIT_WINDOW_SEC", "60"))
    _rate_limit_max_requests = int(
        os.environ.get(
            "GOAT_RATE_LIMIT_MAX_REQUESTS", str(_default_rate_limit_max_requests)
        )
    )
    _ollama_max_concurrent_requests = int(
        os.environ.get("GOAT_OLLAMA_MAX_CONCURRENT_REQUESTS", "2")
    )
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
    if _rate_limit_window_sec < 1:
        raise ValueError("GOAT_RATE_LIMIT_WINDOW_SEC must be >= 1")
    if _rate_limit_max_requests < 1:
        raise ValueError("GOAT_RATE_LIMIT_MAX_REQUESTS must be >= 1")
    if _ollama_max_concurrent_requests < 1:
        raise ValueError("GOAT_OLLAMA_MAX_CONCURRENT_REQUESTS must be >= 1")
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
    _object_store_backend = (
        os.environ.get("GOAT_OBJECT_STORE_BACKEND", "local").strip().lower()
    )
    if _object_store_backend not in {"local", "s3"}:
        raise ValueError("GOAT_OBJECT_STORE_BACKEND must be one of: local, s3")
    _object_store_bucket = os.environ.get("GOAT_OBJECT_STORE_BUCKET", "").strip()
    _object_store_prefix = (
        os.environ.get("GOAT_OBJECT_STORE_PREFIX", "")
        .strip()
        .strip("/")
        .replace("\\", "/")
    )
    _object_store_endpoint_url = os.environ.get(
        "GOAT_OBJECT_STORE_ENDPOINT_URL", ""
    ).strip()
    _object_store_region = os.environ.get("GOAT_OBJECT_STORE_REGION", "").strip()
    _object_store_access_key_id = os.environ.get(
        "GOAT_OBJECT_STORE_ACCESS_KEY_ID", ""
    ).strip()
    _object_store_secret_access_key = os.environ.get(
        "GOAT_OBJECT_STORE_SECRET_ACCESS_KEY", ""
    ).strip()
    _object_store_s3_addressing_style = (
        os.environ.get("GOAT_OBJECT_STORE_S3_ADDRESSING_STYLE", "auto").strip().lower()
    )
    if _object_store_s3_addressing_style not in {"auto", "path", "virtual"}:
        raise ValueError(
            "GOAT_OBJECT_STORE_S3_ADDRESSING_STYLE must be one of: auto, path, virtual"
        )
    if _object_store_backend == "s3" and not _object_store_bucket:
        raise ValueError("GOAT_OBJECT_STORE_BUCKET is required when backend is s3")
    _runtime_metadata_backend = (
        os.environ.get("GOAT_RUNTIME_METADATA_BACKEND", "sqlite").strip().lower()
    )
    if _runtime_metadata_backend not in {"sqlite", "postgres"}:
        raise ValueError(
            "GOAT_RUNTIME_METADATA_BACKEND must be one of: sqlite, postgres"
        )
    _runtime_postgres_dsn = os.environ.get("GOAT_RUNTIME_POSTGRES_DSN", "").strip()
    if _runtime_metadata_backend == "postgres":
        if not _runtime_postgres_dsn:
            raise ValueError(
                "GOAT_RUNTIME_POSTGRES_DSN is required when "
                "GOAT_RUNTIME_METADATA_BACKEND=postgres"
            )
        if _deploy_mode != REMOTE_DEPLOY_MODE:
            raise ValueError(
                "GOAT_RUNTIME_METADATA_BACKEND=postgres currently requires "
                "GOAT_DEPLOY_MODE=2"
            )
    _feature_sandbox = _env_bool("GOAT_FEATURE_CODE_SANDBOX", "false")
    _feature_agent_workbench = _env_bool("GOAT_FEATURE_AGENT_WORKBENCH", "false")
    _workbench_web_provider = (
        os.environ.get("GOAT_WORKBENCH_WEB_PROVIDER", "duckduckgo").strip().lower()
    )
    _workbench_web_max_results = int(
        os.environ.get("GOAT_WORKBENCH_WEB_MAX_RESULTS", "6")
    )
    _workbench_web_timeout_sec = int(
        os.environ.get("GOAT_WORKBENCH_WEB_TIMEOUT_SEC", "15")
    )
    _workbench_web_region = (
        os.environ.get("GOAT_WORKBENCH_WEB_REGION", "wt-wt").strip().lower()
    )
    _workbench_web_safesearch = (
        os.environ.get("GOAT_WORKBENCH_WEB_SAFESEARCH", "moderate").strip().lower()
    )
    _workbench_langgraph_enabled = _env_bool("GOAT_WORKBENCH_LANGGRAPH_ENABLED", "true")
    _workbench_browse_max_steps = int(
        os.environ.get("GOAT_WORKBENCH_BROWSE_MAX_STEPS", "2")
    )
    _workbench_deep_research_max_steps = int(
        os.environ.get("GOAT_WORKBENCH_DEEP_RESEARCH_MAX_STEPS", "3")
    )
    _workbench_connector_bindings_json = os.environ.get(
        "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON", ""
    ).strip()
    _sandbox_provider = (
        os.environ.get("GOAT_CODE_SANDBOX_PROVIDER", "docker").strip().lower()
    )
    _docker_sock = os.environ.get("GOAT_DOCKER_SOCKET", "").strip()
    _sandbox_image = os.environ.get(
        "GOAT_CODE_SANDBOX_DEFAULT_IMAGE", "python:3.12-slim"
    ).strip()
    _sandbox_localhost_shell = os.environ.get(
        "GOAT_CODE_SANDBOX_LOCALHOST_SHELL", ""
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
    if _sandbox_provider not in {"docker", "localhost"}:
        raise ValueError("GOAT_CODE_SANDBOX_PROVIDER must be one of: docker, localhost")
    if _workbench_web_provider not in {"disabled", "duckduckgo"}:
        raise ValueError(
            "GOAT_WORKBENCH_WEB_PROVIDER must be one of: disabled, duckduckgo"
        )
    if _workbench_web_max_results < 1 or _workbench_web_max_results > 10:
        raise ValueError("GOAT_WORKBENCH_WEB_MAX_RESULTS must be between 1 and 10")
    if _workbench_web_timeout_sec < 1:
        raise ValueError("GOAT_WORKBENCH_WEB_TIMEOUT_SEC must be >= 1")
    if not _workbench_web_region:
        raise ValueError("GOAT_WORKBENCH_WEB_REGION must not be empty")
    if _workbench_web_safesearch not in {"on", "moderate", "off"}:
        raise ValueError(
            "GOAT_WORKBENCH_WEB_SAFESEARCH must be one of: on, moderate, off"
        )
    if _workbench_browse_max_steps < 1 or _workbench_browse_max_steps > 4:
        raise ValueError("GOAT_WORKBENCH_BROWSE_MAX_STEPS must be between 1 and 4")
    if _workbench_deep_research_max_steps < 1 or _workbench_deep_research_max_steps > 6:
        raise ValueError(
            "GOAT_WORKBENCH_DEEP_RESEARCH_MAX_STEPS must be between 1 and 6"
        )
    if _workbench_connector_bindings_json:
        parse_workbench_connector_bindings_json(_workbench_connector_bindings_json)
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
    _account_auth_enabled = _env_bool("GOAT_ACCOUNT_AUTH_ENABLED", "false")
    _browser_session_secret = os.environ.get("GOAT_BROWSER_SESSION_SECRET", "").strip()
    _account_session_ttl_sec = int(
        os.environ.get("GOAT_ACCOUNT_SESSION_TTL_SEC", str(60 * 60 * 24 * 30))
    )
    _google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    _google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    _google_redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    _google_oauth_state_ttl_sec = int(
        os.environ.get("GOAT_GOOGLE_OAUTH_STATE_TTL_SEC", str(60 * 10))
    )
    _shared_access_password = os.environ.get("GOAT_SHARED_ACCESS_PASSWORD", "").strip()
    _shared_access_password_hash = os.environ.get(
        "GOAT_SHARED_ACCESS_PASSWORD_HASH", ""
    ).strip()
    _shared_access_session_secret = os.environ.get(
        "GOAT_SHARED_ACCESS_SESSION_SECRET", ""
    ).strip()
    _shared_access_session_ttl_sec = int(
        os.environ.get("GOAT_SHARED_ACCESS_SESSION_TTL_SEC", str(60 * 60 * 24 * 30))
    )
    _require_session_owner = _env_bool("GOAT_REQUIRE_SESSION_OWNER", "false")
    if _api_key_write and not _api_key:
        raise ValueError(
            "GOAT_API_KEY_WRITE requires GOAT_API_KEY (read key) to be set."
        )
    if _account_session_ttl_sec < 1:
        raise ValueError("GOAT_ACCOUNT_SESSION_TTL_SEC must be >= 1")
    if _google_oauth_state_ttl_sec < 1:
        raise ValueError("GOAT_GOOGLE_OAUTH_STATE_TTL_SEC must be >= 1")
    google_envs = (
        _google_client_id,
        _google_client_secret,
        _google_redirect_uri,
    )
    if any(google_envs) and not all(google_envs):
        raise ValueError(
            "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI must all be set together."
        )
    if (_account_auth_enabled or all(google_envs)) and not _browser_session_secret:
        raise ValueError(
            "GOAT_BROWSER_SESSION_SECRET is required when account browser auth is enabled."
        )
    if all(google_envs) and not _account_auth_enabled:
        raise ValueError("Google OAuth requires GOAT_ACCOUNT_AUTH_ENABLED=true.")
    _validate_pwdlib_hash(_shared_access_password_hash)
    if _shared_access_session_ttl_sec < 1:
        raise ValueError("GOAT_SHARED_ACCESS_SESSION_TTL_SEC must be >= 1")
    if (
        _shared_access_password or _shared_access_password_hash
    ) and not _shared_access_session_secret:
        raise ValueError(
            "GOAT_SHARED_ACCESS_SESSION_SECRET is required when "
            "shared browser access is enabled."
        )
    log_db_path = _resolve_env_path(
        os.environ.get("GOAT_LOG_PATH", str(_default_log_db)),
        relative_to=APP_ROOT,
    )
    log_dir = _ensure_directory(
        _resolve_env_path(
            os.environ.get("GOAT_LOG_DIR", str(_default_log_dir)),
            relative_to=APP_ROOT,
        ),
        label="GOAT_LOG_DIR",
    )
    data_dir = _ensure_directory(
        _resolve_env_path(
            os.environ.get("GOAT_DATA_DIR", str(_default_data_dir)),
            relative_to=APP_ROOT,
        ),
        label="GOAT_DATA_DIR",
    )
    object_store_root = _resolve_env_path(
        os.environ.get("GOAT_OBJECT_STORE_ROOT", str(data_dir)),
        relative_to=APP_ROOT,
    )
    if _object_store_backend == "local":
        object_store_root = _ensure_directory(
            object_store_root,
            label="GOAT_OBJECT_STORE_ROOT",
        )
    if log_db_path.exists() and log_db_path.is_dir():
        raise ValueError(f"GOAT_LOG_PATH must point to a file path: {log_db_path}")
    log_db_path.parent.mkdir(parents=True, exist_ok=True)
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
        runtime_root=runtime_root,
        logo_svg=APP_ROOT / "static" / "urochester_simon_business_horizontal.svg",
        log_dir=log_dir,
        log_db_path=log_db_path,
        data_dir=data_dir,
        runtime_metadata_backend=cast(
            RuntimeMetadataBackendId, _runtime_metadata_backend
        ),
        runtime_postgres_dsn=_runtime_postgres_dsn,
        object_store_backend=cast(ObjectStoreBackendId, _object_store_backend),
        object_store_root=object_store_root,
        object_store_bucket=_object_store_bucket,
        object_store_prefix=_object_store_prefix,
        object_store_endpoint_url=_object_store_endpoint_url,
        object_store_region=_object_store_region,
        object_store_access_key_id=_object_store_access_key_id,
        object_store_secret_access_key=_object_store_secret_access_key,
        object_store_s3_addressing_style=cast(
            ObjectStoreS3AddressingStyle, _object_store_s3_addressing_style
        ),
        api_key=_api_key,
        api_key_write=_api_key_write,
        api_credentials_json=_api_credentials_json,
        account_auth_enabled=_account_auth_enabled,
        browser_session_secret=_browser_session_secret,
        account_session_ttl_sec=_account_session_ttl_sec,
        google_client_id=_google_client_id,
        google_client_secret=_google_client_secret,
        google_redirect_uri=_google_redirect_uri,
        google_oauth_state_ttl_sec=_google_oauth_state_ttl_sec,
        shared_access_password=_shared_access_password,
        shared_access_password_hash=_shared_access_password_hash,
        shared_access_session_secret=_shared_access_session_secret,
        shared_access_session_ttl_sec=_shared_access_session_ttl_sec,
        require_session_owner=_require_session_owner,
        rate_limit_window_sec=_rate_limit_window_sec,
        rate_limit_max_requests=_rate_limit_max_requests,
        ollama_max_concurrent_requests=_ollama_max_concurrent_requests,
        deploy_mode=cast(DeployMode, _deploy_mode),
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
        workbench_web_provider=cast(WorkbenchWebProviderId, _workbench_web_provider),
        workbench_web_max_results=_workbench_web_max_results,
        workbench_web_timeout_sec=_workbench_web_timeout_sec,
        workbench_web_region=_workbench_web_region,
        workbench_web_safesearch=cast(
            Literal["on", "moderate", "off"], _workbench_web_safesearch
        ),
        workbench_langgraph_enabled=_workbench_langgraph_enabled,
        workbench_browse_max_steps=_workbench_browse_max_steps,
        workbench_deep_research_max_steps=_workbench_deep_research_max_steps,
        workbench_connector_bindings_json=_workbench_connector_bindings_json,
        code_sandbox_provider=cast(CodeSandboxProviderId, _sandbox_provider),
        docker_socket_path=_docker_sock,
        code_sandbox_default_image=_sandbox_image,
        code_sandbox_localhost_shell=_sandbox_localhost_shell,
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
