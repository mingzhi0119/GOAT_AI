"""Load / latency smoke against a running GOAT API (Phase 13.3).

Run from the repository root::

    python -m tools.load_chat_smoke --base-url http://127.0.0.1:62606 --model <name> --runs 20
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import uuid
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class RunSample:
    total_ms: float
    first_token_ms: float | None


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * q))))
    return float(ordered[idx])


def _read_sse_sample(
    *,
    base_url: str,
    model: str,
    timeout_sec: int,
    api_key: str,
    index: int,
) -> RunSample:
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "session_id": f"load-smoke-{index}",
        "messages": [{"role": "user", "content": "Reply with one short sentence."}],
    }
    headers: dict[str, str] = {}
    if api_key:
        headers["X-GOAT-API-Key"] = api_key
    headers["X-Request-ID"] = str(uuid.uuid4())

    started = time.perf_counter()
    first_token_ms: float | None = None
    with requests.post(
        url,
        json=payload,
        headers=headers,
        stream=True,
        timeout=timeout_sec,
    ) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data: "):
                continue
            data = raw_line[6:]
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            if event_type == "token" and first_token_ms is None:
                first_token_ms = (time.perf_counter() - started) * 1000.0
            if event_type == "done":
                break
    total_ms = (time.perf_counter() - started) * 1000.0
    return RunSample(total_ms=total_ms, first_token_ms=first_token_ms)


def _print_summary(samples: list[RunSample]) -> None:
    total = [item.total_ms for item in samples]
    first = [item.first_token_ms for item in samples if item.first_token_ms is not None]
    print("load_chat_smoke summary")
    print(f"- runs: {len(samples)}")
    print(f"- total avg_ms: {statistics.fmean(total):.1f}")
    print(f"- total p50_ms: {_percentile(total, 0.50):.1f}")
    print(f"- total p95_ms: {_percentile(total, 0.95):.1f}")
    if first:
        print(f"- first_token avg_ms: {statistics.fmean(first):.1f}")
        print(f"- first_token p50_ms: {_percentile(first, 0.50):.1f}")
        print(f"- first_token p95_ms: {_percentile(first, 0.95):.1f}")


def _print_system_inference(*, base_url: str, api_key: str, timeout_sec: int) -> None:
    url = f"{base_url.rstrip('/')}/api/system/inference"
    headers: dict[str, str] = {}
    if api_key:
        headers["X-GOAT-API-Key"] = api_key
    response = requests.get(url, headers=headers, timeout=timeout_sec)
    response.raise_for_status()
    body = response.json()
    print("system_inference snapshot")
    print(f"- chat_p50_ms: {body.get('chat_p50_ms')}")
    print(f"- chat_p95_ms: {body.get('chat_p95_ms')}")
    print(f"- first_token_p50_ms: {body.get('first_token_p50_ms')}")
    print(f"- first_token_p95_ms: {body.get('first_token_p95_ms')}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load smoke test for POST /api/chat SSE."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:62606")
    parser.add_argument("--model", default="gemma4:26b")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--show-system-inference", action="store_true")
    args = parser.parse_args()

    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")

    samples: list[RunSample] = []
    for index in range(args.runs):
        sample = _read_sse_sample(
            base_url=args.base_url,
            model=args.model,
            timeout_sec=args.timeout_sec,
            api_key=args.api_key,
            index=index,
        )
        samples.append(sample)

    _print_summary(samples)
    if args.show_system_inference:
        _print_system_inference(
            base_url=args.base_url,
            api_key=args.api_key,
            timeout_sec=args.timeout_sec,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
