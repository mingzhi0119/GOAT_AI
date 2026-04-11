"""Generate ``docs/api.llm.yaml`` from ``docs/openapi.json``.

Run from the repository root::

    python -m tools.generate_llm_api_yaml
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = REPO_ROOT / "docs" / "openapi.json"
OUTPUT_PATH = REPO_ROOT / "docs" / "api.llm.yaml"

COMMON_ERRORS: dict[str, dict[str, str]] = {
    "400": {"detail": "bad request"},
    "401": {"detail": "invalid or missing api key"},
    "404": {"detail": "not found"},
    "422": {"detail": "validation error"},
    "429": {"detail": "too many requests"},
    "503": {"detail": "ai backend unavailable"},
}


def _load_openapi(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _component_ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _render_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    safe_plain = (
        text
        and "\n" not in text
        and not text.startswith(
            ("{", "[", "-", "!", "&", "*", "#", "?", ":", "@", "`", '"', "'")
        )
        and ": " not in text
        and text not in {"null", "true", "false"}
    )
    return text if safe_plain else json.dumps(text, ensure_ascii=False)


def _yaml_lines(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [f"{prefix}{{}}"]
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_render_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}[]"]
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                nested = _yaml_lines(item, indent + 2)
                first = nested[0].lstrip()
                lines.append(f"{prefix}- {first}")
                lines.extend(nested[1:])
            else:
                lines.append(f"{prefix}- {_render_scalar(item)}")
        return lines
    return [f"{prefix}{_render_scalar(value)}"]


def _schema_type(schema: dict[str, Any]) -> str:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return _component_ref_name(ref)

    if "anyOf" in schema:
        variants = [_schema_type(item) for item in schema["anyOf"]]
        deduped: list[str] = []
        for item in variants:
            if item not in deduped:
                deduped.append(item)
        return "|".join(deduped)

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return "|".join(str(item) for item in enum_values)

    schema_type = schema.get("type")
    if schema_type == "array":
        items = schema.get("items", {})
        return f"{_schema_type(items)}[]"
    if schema_type == "object":
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"map[string,{_schema_type(additional)}]"
        return "object"
    if schema_type is not None:
        return str(schema_type)
    if "contentMediaType" in schema:
        return "binary"
    return "any"


def _schema_summary(schema: dict[str, Any]) -> dict[str, Any]:
    schema_type = schema.get("type")
    summary: dict[str, Any] = {"type": _schema_type(schema)}

    required = schema.get("required")
    if isinstance(required, list) and required:
        summary["required"] = required

    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        summary["properties"] = {
            key: _schema_type(value) for key, value in properties.items()
        }

    if schema_type == "array" and "items" in schema:
        summary["items"] = _schema_type(schema["items"])

    return summary


def _extract_body_schema_name(operation: dict[str, Any]) -> str | dict[str, Any] | None:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None

    content = request_body.get("content", {})
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        return _schema_type(schema)

    if "multipart/form-data" in content:
        schema = content["multipart/form-data"].get("schema", {})
        body_fields: dict[str, str] = {}
        ref = schema.get("$ref")
        if isinstance(ref, str):
            body_schema = _component_ref_name(ref)
            body_fields["file"] = "binary"
            return {
                "content_type": "multipart/form-data",
                "fields": body_fields,
                "schema": body_schema,
            }
        return {"content_type": "multipart/form-data"}

    return None


def _response_schema(operation: dict[str, Any], status_code: str) -> Any:
    responses = operation.get("responses", {})
    response = responses.get(status_code, {})
    if not isinstance(response, dict):
        return None

    content = response.get("content", {})
    if "text/event-stream" in content:
        path_hint = str(operation.get("x-goat-path", ""))
        if path_hint.endswith("/code-sandbox/executions/{execution_id}/logs"):
            return {
                "content_type": "text/event-stream",
                "stream": [
                    {
                        "status": {
                            "type": "status",
                            "execution_id": "string",
                            "status": "queued|running|completed|failed|denied",
                            "provider_name": "string",
                            "updated_at": "string",
                            "timed_out": "boolean",
                        }
                    },
                    {
                        "stdout": {
                            "type": "stdout",
                            "execution_id": "string",
                            "sequence": "integer",
                            "created_at": "string",
                            "chunk": "string",
                        }
                    },
                    {
                        "stderr": {
                            "type": "stderr",
                            "execution_id": "string",
                            "sequence": "integer",
                            "created_at": "string",
                            "chunk": "string",
                        }
                    },
                    {"done": {"type": "done"}},
                    {"error_frame": {"type": "error", "message": "string"}},
                ],
            }
        path = operation.get("operationId", "")
        if "chat" in path:
            return {
                "content_type": "text/event-stream",
                "stream": [
                    {"token": {"type": "token", "token": "string"}},
                    {"chart_spec": "ChartSpec"},
                    {
                        "artifact": {
                            "type": "artifact",
                            "artifact_id": "string",
                            "filename": "string",
                            "mime_type": "string",
                            "byte_size": "integer",
                            "download_url": "string",
                            "source_message_id": "string|null",
                        }
                    },
                    {"done": {"type": "done"}},
                    {"error_frame": {"type": "error", "message": "string"}},
                ],
            }
        if "upload" in path:
            return {
                "content_type": "text/event-stream",
                "stream": [
                    {
                        "file_prompt": {
                            "type": "file_prompt",
                            "filename": "string",
                            "suffix_prompt": "string",
                        }
                    },
                    {
                        "knowledge_ready": {
                            "type": "knowledge_ready",
                            "filename": "string",
                            "suffix_prompt": "string",
                            "document_id": "string",
                            "ingestion_id": "string",
                            "status": "string",
                            "retrieval_mode": "string",
                            "template_prompt": "string",
                        }
                    },
                    {"done": {"type": "done"}},
                    {"error_frame": {"type": "error", "message": "string"}},
                ],
            }
        return {
            "content_type": "text/event-stream",
            "stream": [
                {
                    "file_context": {
                        "type": "object",
                        "properties": {
                            "type": "file_context",
                            "filename": "string",
                            "prompt": "string",
                        },
                    }
                },
                {"done": {"type": "done"}},
                {"error_frame": {"type": "error", "message": "string"}},
            ],
        }

    json_content = content.get("application/json")
    if isinstance(json_content, dict):
        schema = json_content.get("schema", {})
        return (
            _schema_type(schema)
            if "$ref" in schema or "type" in schema or "anyOf" in schema
            else "object"
        )

    if status_code == "204":
        return "no_content"

    return None


def _operation_name(path: str, method: str, operation: dict[str, Any]) -> str:
    operation_id = operation.get("operationId")
    if isinstance(operation_id, str) and operation_id:
        return operation_id.split("_api_")[0]
    cleaned = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f"{method.lower()}_{cleaned or 'root'}"


def _path_without_prefix(path: str, prefix: str) -> str:
    if path.startswith(prefix):
        trimmed = path[len(prefix) :]
        return trimmed or "/"
    return path


def _build_compact_spec(openapi: dict[str, Any]) -> dict[str, Any]:
    title = openapi.get("info", {}).get("title", "API")
    openapi_version = openapi.get("openapi", "")
    paths = openapi.get("paths", {})
    components = openapi.get("components", {}).get("schemas", {})
    base_path = "/api"

    compact: dict[str, Any] = {
        "format": "llm-compact-api",
        "source": {
            "canonical_openapi": "docs/openapi.json",
            "openapi_version": openapi_version,
            "generated_from": "backend.main:app",
            "purpose": "Minimal API context for LLM consumption",
        },
        "api": {
            "name": title,
            "base_path": base_path,
            "auth": {
                "scheme": "api_key_optional",
                "header": "X-GOAT-API-Key",
                "applies_to": "all_except_health",
            },
            "common_headers": {
                "response": {
                    "X-Request-ID": "request trace id",
                    "Retry-After": "present on 429",
                }
            },
            "common_errors": COMMON_ERRORS,
        },
        "schemas": {},
        "endpoints": [],
    }

    for name, schema in components.items():
        if name.startswith(("HTTPValidationError", "ValidationError", "Body_")):
            continue
        compact["schemas"][name] = _schema_summary(schema)

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue

            endpoint: dict[str, Any] = {
                "op": _operation_name(path, method, operation),
                "method": method.upper(),
                "path": _path_without_prefix(path, base_path),
            }
            operation = dict(operation)
            operation["x-goat-path"] = path

            if path == f"{base_path}/health":
                endpoint["auth"] = "none"

            parameters = operation.get("parameters", [])
            path_params = {
                item["name"]: _schema_type(item.get("schema", {}))
                for item in parameters
                if isinstance(item, dict) and item.get("in") == "path"
            }
            if path_params:
                endpoint["path_params"] = path_params

            body = _extract_body_schema_name(operation)
            if isinstance(body, str):
                endpoint["body"] = body
                endpoint["content_type"] = "application/json"
            elif isinstance(body, dict):
                endpoint["body"] = body

            responses: dict[str, Any] = {}
            error_codes: list[int] = []
            for status_code in operation.get("responses", {}):
                if status_code.isdigit() and int(status_code) >= 400:
                    error_codes.append(int(status_code))
                    continue
                response_value = _response_schema(operation, status_code)
                if response_value is not None:
                    responses[status_code] = response_value

            if error_codes:
                responses["errors"] = sorted(error_codes)

            endpoint["response"] = responses
            compact["endpoints"].append(endpoint)

    return compact


def _write_yaml(document: dict[str, Any], path: Path) -> None:
    yaml_text = "\n".join(_yaml_lines(document)) + "\n"
    path.write_text(yaml_text, encoding="utf-8")


def main() -> None:
    openapi = _load_openapi(OPENAPI_PATH)
    compact = _build_compact_spec(openapi)
    _write_yaml(compact, OUTPUT_PATH)
    print(
        f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)} from {OPENAPI_PATH.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
