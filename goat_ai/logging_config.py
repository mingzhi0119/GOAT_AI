from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from goat_ai.config import load_dotenv_if_present
from goat_ai.request_context import get_request_id


class RequestContextFilter(logging.Filter):
    """Attach ``request_id`` to every log record for text or JSON formatters."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = get_request_id()
        record.request_id = rid if rid else ""  # type: ignore[attr-defined]
        return True


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line; includes correlation id and optional structured ``extra``."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = getattr(record, "request_id", "") or get_request_id()
        if rid:
            payload["request_id"] = rid
        for key in (
            "route",
            "status",
            "duration_ms",
            "event",
            "component",
            "db_path",
            "session_id",
            "code",
            "operation",
        ):
            if hasattr(record, key):
                val = getattr(record, key)
                if val is not None and val != "":
                    payload[key] = val
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info).strip()
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure root logging once (idempotent). Honors ``GOAT_LOG_JSON`` after ``.env`` load."""
    load_dotenv_if_present()
    if logging.getLogger().handlers:
        return
    use_json = os.environ.get("GOAT_LOG_JSON", "false").lower() in ("1", "true", "yes")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.addFilter(RequestContextFilter())
    if use_json:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
            ),
        )
    root.addHandler(handler)
