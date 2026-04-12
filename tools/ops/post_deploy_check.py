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


def _headers(api_key: str, owner_id: str = "") -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key:
        headers["X-GOAT-API-Key"] = api_key
    if owner_id:
        headers["X-GOAT-Owner-Id"] = owner_id
    return headers


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


def _expect_runtime_target(base_url: str, api_key: str, owner_id: str = "") -> int:
    response = requests.get(
        f"{base_url}/api/system/runtime-target",
        headers=_headers(api_key, owner_id),
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    ordered = body.get("ordered_targets", [])
    if not isinstance(ordered, list) or not ordered:
        return _fail("runtime-target ordered_targets is empty")
    first = ordered[0]
    if not isinstance(first, dict) or int(first.get("port", -1)) != 62606:
        return _fail("runtime-target first port is not 62606")
    return 0


def _resolve_chat_check_model(base_url: str, api_key: str, owner_id: str = "") -> str:
    response = requests.get(
        f"{base_url}/api/models",
        headers=_headers(api_key, owner_id),
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    models = body.get("models", [])
    if not isinstance(models, list) or not models:
        raise ValueError("models endpoint returned no available models")
    normalized = [str(model) for model in models if str(model).strip()]
    if not normalized:
        raise ValueError("models endpoint returned no usable model names")
    if "gemma4:26b" in normalized:
        return "gemma4:26b"
    return normalized[0]


def _expect_chat_stream_contract(
    base_url: str, api_key: str, owner_id: str = ""
) -> int:
    timeout_sec = _first_event_timeout_sec()
    model = _resolve_chat_check_model(base_url, api_key, owner_id)
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": "Say hello in three short tokens."}
                ],
                # Quick mode avoids thinking-only streams that consume the whole
                # budget before any answer tokens (thinking models + low max_tokens).
                "think": False,
                "max_tokens": 48,
                "temperature": 0,
            },
            headers=_headers(api_key, owner_id),
            timeout=(5, timeout_sec),
        )
        response.raise_for_status()
        body = response.text
        events = _parse_sse_events(body)
        if not events:
            return _fail("chat stream produced no SSE events")

        first_event = events[0]
        event_type = str(first_event.get("type"))
        if event_type == "error":
            return _fail(
                f"chat stream first event was error: {first_event.get('message', '')}"
            )

        token_events = [e for e in events if str(e.get("type")) == "token"]
        thinking_events = [e for e in events if str(e.get("type")) == "thinking"]
        if token_events or thinking_events:
            return 0
        return _fail(
            f"chat stream produced no token or thinking events (first frame type was {event_type!r})"
        )
    except requests.Timeout as exc:
        return _fail(
            f"chat stream produced no SSE events before first-token timeout: {exc}"
        )
    except json.JSONDecodeError as exc:
        return _fail(f"chat stream returned malformed SSE JSON: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify GOAT AI post-deploy API contract checks."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:62606")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--owner-id", default="")
    args = parser.parse_args()
    base_url = str(args.base_url).rstrip("/")
    api_key = str(args.api_key).strip()
    owner_id = str(args.owner_id).strip()

    health = requests.get(
        f"{base_url}/api/health",
        headers=_headers(api_key, owner_id),
        timeout=10,
    )
    if health.status_code != 200:
        return _fail(f"health check returned HTTP {health.status_code}")

    ready = requests.get(
        f"{base_url}/api/ready",
        headers=_headers(api_key, owner_id),
        timeout=15,
    )
    if ready.status_code != 200:
        return _fail(
            f"ready check returned HTTP {ready.status_code}: {ready.text[:500]}"
        )
    try:
        ready_body = ready.json()
    except json.JSONDecodeError:
        return _fail("ready check returned non-JSON body")
    if not ready_body.get("ready"):
        return _fail(f"ready check reports not ready: {ready_body!r}")

    for check in (_expect_runtime_target, _expect_chat_stream_contract):
        try:
            result = check(base_url, api_key, owner_id)
            if result != 0:
                return result
        except Exception as exc:
            return _fail(f"{check.__name__} exception: {exc}")

    print("POST_DEPLOY_CHECK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
