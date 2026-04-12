"""Run a lightweight pre-merge latency gate against the in-process contract app."""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from backend.platform.config import get_settings
from backend.platform.dependencies import get_llm_client, get_title_generator
from backend.main import create_contract_app
from backend.services import log_service
from goat_ai.config.settings import Settings
from goat_ai.telemetry.latency_metrics import init_latency_metrics
from goat_ai.shared.types import ChatTurn


@dataclass(frozen=True)
class GateSample:
    total_ms: float


@dataclass(frozen=True)
class GateSummary:
    runs: int
    total_avg_ms: float
    total_p50_ms: float
    total_p95_ms: float
    inference_chat_sample_count: int
    inference_chat_p95_ms: float
    inference_first_token_sample_count: int
    inference_first_token_p95_ms: float


class GateLLM:
    def list_model_names(self) -> list[str]:
        return ["gate-model"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return ["completion"], 8192

    def get_model_capabilities(self, model: str) -> list[str]:
        return ["completion"]

    def get_model_context_length(self, model: str) -> int | None:
        return 8192

    def supports_tool_calling(self, model: str) -> bool:
        return False

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
        last_user_images_base64: list[str] | None = None,
    ):
        _ = (model, messages, system_prompt, ollama_options, last_user_images_base64)
        yield "Latency"
        yield " gate"
        yield " ok"


class GateTitleGenerator:
    def generate_title(
        self,
        *,
        model: str,
        user_text: str,
        assistant_text: str,
    ) -> str | None:
        _ = (model, user_text, assistant_text)
        return "Latency gate session"


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * q))))
    return float(ordered[idx])


def _build_settings(root: Path) -> Settings:
    runtime_root = root / "var"
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="latency gate system prompt",
        app_root=root,
        logo_svg=root / "logo.svg",
        runtime_root=runtime_root,
        log_dir=runtime_root / "logs",
        log_db_path=runtime_root / "chat_logs.db",
        data_dir=runtime_root / "data",
        ready_skip_ollama_probe=True,
    )


def _run_chat_sample(client: TestClient, index: int) -> GateSample:
    started = time.perf_counter()
    response = client.post(
        "/api/chat",
        json={
            "model": "gate-model",
            "session_id": f"pr-latency-gate-{index}",
            "messages": [{"role": "user", "content": "Reply with one short sentence."}],
        },
    )
    total_ms = (time.perf_counter() - started) * 1000.0
    response.raise_for_status()
    if '"type":"done"' not in response.text.replace(" ", ""):
        raise ValueError("Chat smoke response did not emit a done SSE frame.")
    return GateSample(total_ms=total_ms)


def _build_summary(
    samples: list[GateSample], inference_body: dict[str, object]
) -> GateSummary:
    totals = [sample.total_ms for sample in samples]
    return GateSummary(
        runs=len(samples),
        total_avg_ms=statistics.fmean(totals),
        total_p50_ms=_percentile(totals, 0.50),
        total_p95_ms=_percentile(totals, 0.95),
        inference_chat_sample_count=int(inference_body.get("chat_sample_count", 0)),
        inference_chat_p95_ms=float(inference_body.get("chat_p95_ms", 0.0)),
        inference_first_token_sample_count=int(
            inference_body.get("first_token_sample_count", 0)
        ),
        inference_first_token_p95_ms=float(
            inference_body.get("first_token_p95_ms", 0.0)
        ),
    )


def _check_budget(label: str, measured_ms: float, max_allowed_ms: float) -> str | None:
    if measured_ms <= max_allowed_ms:
        return None
    return f"{label} exceeded budget: {measured_ms:.1f} ms > {max_allowed_ms:.1f} ms"


def evaluate_gate(
    summary: GateSummary,
    *,
    max_total_p95_ms: float,
    max_first_token_p95_ms: float,
) -> list[str]:
    failures = [
        _check_budget(
            "chat total p95 (wall clock)",
            summary.total_p95_ms,
            max_total_p95_ms,
        ),
        _check_budget(
            "chat total p95 (system inference)",
            summary.inference_chat_p95_ms,
            max_total_p95_ms,
        ),
        _check_budget(
            "first-token p95 (system inference)",
            summary.inference_first_token_p95_ms,
            max_first_token_p95_ms,
        ),
    ]
    if summary.inference_chat_sample_count < summary.runs:
        failures.append(
            "system inference chat sample count was lower than the number of gate runs"
        )
    if summary.inference_first_token_sample_count < summary.runs:
        failures.append(
            "system inference first-token sample count was lower than the number of gate runs"
        )
    return [failure for failure in failures if failure]


def write_summary_json(
    *,
    output: Path,
    summary: GateSummary,
    max_total_p95_ms: float,
    max_first_token_p95_ms: float,
    failures: list[str],
) -> None:
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": asdict(summary),
        "budgets": {
            "max_total_p95_ms": max_total_p95_ms,
            "max_first_token_p95_ms": max_first_token_p95_ms,
        },
        "status": "pass" if not failures else "fail",
        "failures": failures,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_pr_latency_gate(*, runs: int) -> GateSummary:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        settings = _build_settings(root)
        log_service.init_db(settings.log_db_path)
        init_latency_metrics(settings.latency_rolling_max_samples)
        app = create_contract_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_llm_client] = lambda: GateLLM()
        app.dependency_overrides[get_title_generator] = lambda: GateTitleGenerator()

        with TestClient(app) as client:
            samples = [_run_chat_sample(client, index) for index in range(runs)]
            inference = client.get("/api/system/inference")
            inference.raise_for_status()
            return _build_summary(samples, inference.json())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a lightweight pre-merge latency gate against the contract app."
    )
    parser.add_argument("--runs", type=int, default=8)
    parser.add_argument("--max-total-p95-ms", type=float, default=1200.0)
    parser.add_argument("--max-first-token-p95-ms", type=float, default=400.0)
    parser.add_argument("--json-output", type=Path, default=None)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")

    summary = run_pr_latency_gate(runs=args.runs)
    print("pr_latency_gate summary")
    print(f"- runs: {summary.runs}")
    print(f"- wall total avg_ms: {summary.total_avg_ms:.1f}")
    print(f"- wall total p50_ms: {summary.total_p50_ms:.1f}")
    print(f"- wall total p95_ms: {summary.total_p95_ms:.1f}")
    print(f"- inference chat_sample_count: {summary.inference_chat_sample_count}")
    print(f"- inference chat_p95_ms: {summary.inference_chat_p95_ms:.1f}")
    print(
        "- inference first_token_sample_count: "
        f"{summary.inference_first_token_sample_count}"
    )
    print(f"- inference first_token_p95_ms: {summary.inference_first_token_p95_ms:.1f}")

    failures = evaluate_gate(
        summary,
        max_total_p95_ms=args.max_total_p95_ms,
        max_first_token_p95_ms=args.max_first_token_p95_ms,
    )
    if args.json_output is not None:
        write_summary_json(
            output=args.json_output,
            summary=summary,
            max_total_p95_ms=args.max_total_p95_ms,
            max_first_token_p95_ms=args.max_first_token_p95_ms,
            failures=failures,
        )
    if failures:
        for failure in failures:
            print(f"PR_LATENCY_GATE_FAILED: {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
