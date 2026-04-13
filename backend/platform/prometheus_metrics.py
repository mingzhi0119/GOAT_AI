"""In-process Prometheus text metrics (Wave A)."""

from __future__ import annotations

import math
import threading
from collections import defaultdict

from goat_ai.telemetry.telemetry_counters import (
    snapshot_feature_gate_denials,
    snapshot_knowledge_query_rewrite_applied,
    snapshot_knowledge_retrieval,
    snapshot_ollama_errors,
)

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

HTTP_REQUESTS_TOTAL = "http_requests_total"
HTTP_REQUEST_DURATION_SECONDS = "http_request_duration_seconds"
CHAT_STREAM_COMPLETED_TOTAL = "chat_stream_completed_total"
OLLAMA_ERRORS_TOTAL = "ollama_errors_total"
SQLITE_LOG_WRITE_FAILURES_TOTAL = "sqlite_log_write_failures_total"
FEATURE_GATE_DENIALS_TOTAL = "feature_gate_denials_total"
KNOWLEDGE_RETRIEVAL_REQUESTS_TOTAL = "knowledge_retrieval_requests_total"
KNOWLEDGE_QUERY_REWRITE_APPLIED_TOTAL = "knowledge_query_rewrite_applied_total"

EXPORTED_METRIC_FAMILIES: frozenset[str] = frozenset(
    {
        HTTP_REQUESTS_TOTAL,
        HTTP_REQUEST_DURATION_SECONDS,
        CHAT_STREAM_COMPLETED_TOTAL,
        OLLAMA_ERRORS_TOTAL,
        SQLITE_LOG_WRITE_FAILURES_TOTAL,
        FEATURE_GATE_DENIALS_TOTAL,
        KNOWLEDGE_RETRIEVAL_REQUESTS_TOTAL,
        KNOWLEDGE_QUERY_REWRITE_APPLIED_TOTAL,
    }
)

EXPORTED_METRIC_LABELS: dict[str, frozenset[str]] = {
    HTTP_REQUESTS_TOTAL: frozenset({"method", "route", "status"}),
    HTTP_REQUEST_DURATION_SECONDS: frozenset({"le"}),
    CHAT_STREAM_COMPLETED_TOTAL: frozenset(),
    OLLAMA_ERRORS_TOTAL: frozenset({"code", "endpoint", "http_status"}),
    SQLITE_LOG_WRITE_FAILURES_TOTAL: frozenset({"operation", "code"}),
    FEATURE_GATE_DENIALS_TOTAL: frozenset({"feature", "gate_kind", "reason"}),
    KNOWLEDGE_RETRIEVAL_REQUESTS_TOTAL: frozenset({"retrieval_profile", "outcome"}),
    KNOWLEDGE_QUERY_REWRITE_APPLIED_TOTAL: frozenset({"retrieval_profile"}),
}


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def record_http_request(
    *, method: str, route: str, status_code: int, duration_sec: float
) -> None:
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
    retr_copy = snapshot_knowledge_retrieval()
    rew_copy = snapshot_knowledge_query_rewrite_applied()

    lines.append(f"# HELP {HTTP_REQUESTS_TOTAL} Total HTTP requests processed.")
    lines.append(f"# TYPE {HTTP_REQUESTS_TOTAL} counter")
    for (method, route, status), count in sorted(http_copy.items()):
        rm = _escape_label_value(method)
        rr = _escape_label_value(route)
        rs = _escape_label_value(status)
        lines.append(
            f'{HTTP_REQUESTS_TOTAL}{{method="{rm}",route="{rr}",status="{rs}"}} {count}'
        )

    lines.append(
        f"# HELP {HTTP_REQUEST_DURATION_SECONDS} HTTP request duration in seconds."
    )
    lines.append(f"# TYPE {HTTP_REQUEST_DURATION_SECONDS} histogram")
    for i, bound in enumerate(_DURATION_BUCKETS):
        le = "+Inf" if math.isinf(bound) else str(bound)
        lines.append(
            f'{HTTP_REQUEST_DURATION_SECONDS}_bucket{{le="{le}"}} {hist_counts[i]}'
        )
    lines.append(f"{HTTP_REQUEST_DURATION_SECONDS}_sum {h_sum}")
    lines.append(f"{HTTP_REQUEST_DURATION_SECONDS}_count {h_cnt}")

    lines.append(
        f"# HELP {CHAT_STREAM_COMPLETED_TOTAL} Chat SSE streams completed with done (success paths)."
    )
    lines.append(f"# TYPE {CHAT_STREAM_COMPLETED_TOTAL} counter")
    lines.append(f"{CHAT_STREAM_COMPLETED_TOTAL} {chat_done}")

    lines.append(f"# HELP {OLLAMA_ERRORS_TOTAL} Ollama HTTP transport failures.")
    lines.append(f"# TYPE {OLLAMA_ERRORS_TOTAL} counter")
    for (code, endpoint, http_status), count in sorted(
        snapshot_ollama_errors().items()
    ):
        c = _escape_label_value(code)
        e = _escape_label_value(endpoint)
        h = _escape_label_value(http_status)
        lines.append(
            f'{OLLAMA_ERRORS_TOTAL}{{code="{c}",endpoint="{e}",http_status="{h}"}} {count}'
        )

    lines.append(
        f"# HELP {SQLITE_LOG_WRITE_FAILURES_TOTAL} SQLite log/session write failures."
    )
    lines.append(f"# TYPE {SQLITE_LOG_WRITE_FAILURES_TOTAL} counter")
    for (operation, code), count in sorted(sqlite_copy.items()):
        op = _escape_label_value(operation)
        c = _escape_label_value(code)
        lines.append(
            f'{SQLITE_LOG_WRITE_FAILURES_TOTAL}{{operation="{op}",code="{c}"}} {count}'
        )

    lines.append(
        f"# HELP {FEATURE_GATE_DENIALS_TOTAL} Feature gate denials by feature, gate kind, and reason (Section 15)."
    )
    lines.append(f"# TYPE {FEATURE_GATE_DENIALS_TOTAL} counter")
    for (feature, gate_kind, reason), count in sorted(fg_copy.items()):
        ff = _escape_label_value(feature)
        gg = _escape_label_value(gate_kind)
        rr = _escape_label_value(reason)
        lines.append(
            f'{FEATURE_GATE_DENIALS_TOTAL}{{feature="{ff}",gate_kind="{gg}",reason="{rr}"}} {count}'
        )

    lines.append(
        f"# HELP {KNOWLEDGE_RETRIEVAL_REQUESTS_TOTAL} "
        "Knowledge search requests by retrieval_profile and outcome (hit=at least one chunk returned)."
    )
    lines.append(f"# TYPE {KNOWLEDGE_RETRIEVAL_REQUESTS_TOTAL} counter")
    for (profile, outcome), count in sorted(retr_copy.items()):
        pp = _escape_label_value(profile)
        oo = _escape_label_value(outcome)
        lines.append(
            f'{KNOWLEDGE_RETRIEVAL_REQUESTS_TOTAL}{{retrieval_profile="{pp}",outcome="{oo}"}} {count}'
        )

    lines.append(
        f"# HELP {KNOWLEDGE_QUERY_REWRITE_APPLIED_TOTAL} "
        "Conservative query rewrite applied (retrieval_profile=rag3_quality) before vector search."
    )
    lines.append(f"# TYPE {KNOWLEDGE_QUERY_REWRITE_APPLIED_TOTAL} counter")
    for profile, count in sorted(rew_copy.items()):
        pp = _escape_label_value(profile)
        lines.append(
            f'{KNOWLEDGE_QUERY_REWRITE_APPLIED_TOTAL}{{retrieval_profile="{pp}"}} {count}'
        )

    return "\n".join(lines) + "\n"
