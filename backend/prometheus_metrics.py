"""In-process Prometheus text metrics (Wave A)."""
from __future__ import annotations

import math
import threading
from collections import defaultdict

from goat_ai.telemetry_counters import snapshot_feature_gate_denials, snapshot_ollama_errors

_lock = threading.Lock()

# http_requests_total{method,route,status}
_http_req: dict[tuple[str, str, str], int] = defaultdict(int)

# Global histogram (low cardinality)
_DURATION_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    float("inf"),
)
_hist_bucket_counts: list[int] = [0] * len(_DURATION_BUCKETS)
_hist_sum: float = 0.0
_hist_count: int = 0

_chat_stream_completed: int = 0
_sqlite_write_failures: dict[tuple[str, str], int] = defaultdict(int)


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def record_http_request(*, method: str, route: str, status_code: int, duration_sec: float) -> None:
    """Record one completed HTTP exchange (including early 401/429 responses)."""
    global _hist_sum, _hist_count
    m = method.upper()
    r = route or "/"
    status = str(int(status_code))
    with _lock:
        _http_req[(m, r, status)] += 1
        _hist_sum += duration_sec
        _hist_count += 1
        for i, bound in enumerate(_DURATION_BUCKETS):
            if duration_sec <= bound:
                _hist_bucket_counts[i] += 1


def inc_chat_stream_completed() -> None:
    """Increment when a chat SSE run emits a successful ``done`` completion."""
    global _chat_stream_completed
    with _lock:
        _chat_stream_completed += 1


def inc_sqlite_log_write_failure(*, operation: str, code: str) -> None:
    """Increment on SQLite write path failure (conversation log or session row)."""
    with _lock:
        _sqlite_write_failures[(operation, code)] += 1


def render_prometheus_text() -> str:
    """Return Prometheus exposition format (text 0.0.4 style)."""
    lines: list[str] = []

    with _lock:
        http_copy = dict(_http_req)
        hist_counts = list(_hist_bucket_counts)
        h_sum = _hist_sum
        h_cnt = _hist_count
        chat_done = _chat_stream_completed
        sqlite_copy = dict(_sqlite_write_failures)

    fg_copy = snapshot_feature_gate_denials()

    lines.append("# HELP http_requests_total Total HTTP requests processed.")
    lines.append("# TYPE http_requests_total counter")
    for (method, route, status), count in sorted(http_copy.items()):
        rm = _escape_label_value(method)
        rr = _escape_label_value(route)
        rs = _escape_label_value(status)
        lines.append(f'http_requests_total{{method="{rm}",route="{rr}",status="{rs}"}} {count}')

    lines.append("# HELP http_request_duration_seconds HTTP request duration in seconds.")
    lines.append("# TYPE http_request_duration_seconds histogram")
    for i, bound in enumerate(_DURATION_BUCKETS):
        le = "+Inf" if math.isinf(bound) else str(bound)
        lines.append(f'http_request_duration_seconds_bucket{{le="{le}"}} {hist_counts[i]}')
    lines.append(f"http_request_duration_seconds_sum {h_sum}")
    lines.append(f"http_request_duration_seconds_count {h_cnt}")

    lines.append("# HELP chat_stream_completed_total Chat SSE streams completed with done (success paths).")
    lines.append("# TYPE chat_stream_completed_total counter")
    lines.append(f"chat_stream_completed_total {chat_done}")

    lines.append("# HELP ollama_errors_total Ollama HTTP transport failures.")
    lines.append("# TYPE ollama_errors_total counter")
    for (code, endpoint, http_status), count in sorted(snapshot_ollama_errors().items()):
        c = _escape_label_value(code)
        e = _escape_label_value(endpoint)
        h = _escape_label_value(http_status)
        lines.append(f'ollama_errors_total{{code="{c}",endpoint="{e}",http_status="{h}"}} {count}')

    lines.append("# HELP sqlite_log_write_failures_total SQLite log/session write failures.")
    lines.append("# TYPE sqlite_log_write_failures_total counter")
    for (operation, code), count in sorted(sqlite_copy.items()):
        op = _escape_label_value(operation)
        c = _escape_label_value(code)
        lines.append(f'sqlite_log_write_failures_total{{operation="{op}",code="{c}"}} {count}')

    lines.append("# HELP feature_gate_denials_total Feature gate denials by feature and reason (§15).")
    lines.append("# TYPE feature_gate_denials_total counter")
    for (feature, reason), count in sorted(fg_copy.items()):
        ff = _escape_label_value(feature)
        rr = _escape_label_value(reason)
        lines.append(f'feature_gate_denials_total{{feature="{ff}",reason="{rr}"}} {count}')

    return "\n".join(lines) + "\n"
