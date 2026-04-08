from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests


def _fail(message: str) -> int:
    print(f"POST_DEPLOY_CHECK_FAILED: {message}")
    return 1


def _parse_sse_events(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _first_event_timeout_sec() -> int:
    raw = os.environ.get("OLLAMA_CHAT_FIRST_EVENT_TIMEOUT", "90").strip()
    try:
        timeout = int(raw)
    except ValueError as exc:  # pragma: no cover - defensive config guard
        raise ValueError("OLLAMA_CHAT_FIRST_EVENT_TIMEOUT must be an integer") from exc
    if timeout < 1:
        raise ValueError("OLLAMA_CHAT_FIRST_EVENT_TIMEOUT must be >= 1")
    return timeout


def _expect_runtime_target(base_url: str) -> int:
    response = requests.get(f"{base_url}/api/system/runtime-target", timeout=10)
    response.raise_for_status()
    body = response.json()
    ordered = body.get("ordered_targets", [])
    if not isinstance(ordered, list) or not ordered:
        return _fail("runtime-target ordered_targets is empty")
    first = ordered[0]
    if not isinstance(first, dict) or int(first.get("port", -1)) != 62606:
        return _fail("runtime-target first port is not 62606")
    return 0


def _expect_chat_stream_contract(base_url: str) -> int:
    timeout_sec = _first_event_timeout_sec()
    response: requests.Response | None = None
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": "gemma4:26b",
                "messages": [{"role": "user", "content": "Say hello in three short tokens."}],
            },
            stream=True,
            timeout=(5, timeout_sec),
        )
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if not isinstance(event, dict):
                return _fail("chat stream returned a non-object SSE payload")
            event_type = str(event.get("type"))
            if event_type == "error":
                return _fail(f"chat stream first event was error: {event.get('message', '')}")
            if event_type != "token":
                return _fail(f"chat stream first event was {event_type!r} instead of token")
            return 0
    except requests.Timeout as exc:
        return _fail(f"chat stream produced no SSE events before first-token timeout: {exc}")
    finally:
        close = getattr(response, "close", None) if response is not None else None
        if callable(close):
            close()
    return _fail("chat stream produced no SSE events")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GOAT AI post-deploy API contract checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:62606")
    args = parser.parse_args()
    base_url = str(args.base_url).rstrip("/")

    health = requests.get(f"{base_url}/api/health", timeout=10)
    if health.status_code != 200:
        return _fail(f"health check returned HTTP {health.status_code}")

    ready = requests.get(f"{base_url}/api/ready", timeout=15)
    if ready.status_code != 200:
        return _fail(f"ready check returned HTTP {ready.status_code}: {ready.text[:500]}")
    try:
        ready_body = ready.json()
    except json.JSONDecodeError:
        return _fail("ready check returned non-JSON body")
    if not ready_body.get("ready"):
        return _fail(f"ready check reports not ready: {ready_body!r}")

    for check in (_expect_runtime_target, _expect_chat_stream_contract):
        try:
            result = check(base_url)
            if result != 0:
                return result
        except Exception as exc:
            return _fail(f"{check.__name__} exception: {exc}")

    print("POST_DEPLOY_CHECK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
