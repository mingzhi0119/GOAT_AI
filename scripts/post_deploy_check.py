from __future__ import annotations

import argparse
import json
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
    response = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": "gemma4:26b",
            "messages": [{"role": "user", "content": "Say hello in three short tokens."}],
        },
        timeout=30,
    )
    response.raise_for_status()
    events = _parse_sse_events(response.text)
    if not events:
        return _fail("chat stream produced no SSE events")
    types = [str(item.get("type")) for item in events]
    if types[-1] != "done":
        return _fail("chat stream did not end with done event")
    if not any(t == "token" for t in types) and not any(t == "error" for t in types):
        return _fail("chat stream produced neither token nor error events")
    return 0


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
