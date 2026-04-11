"""Native function-tool schema for chat-triggered code sandbox execution."""

from __future__ import annotations

from typing import Any


EXECUTE_CODE_SANDBOX_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "execute_code_sandbox",
        "description": (
            "Run short code or shell commands in the server's configured code sandbox "
            "when actual execution is needed to verify behavior, compute results, or "
            "produce output files. Prefer this tool over guessing outputs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "runtime_preset": {
                    "type": "string",
                    "enum": ["shell"],
                    "description": "Execution preset. Phase 20B only supports shell.",
                },
                "code": {
                    "type": "string",
                    "description": "Shell or PowerShell script source to run.",
                },
                "command": {
                    "type": "string",
                    "description": "Optional shell command executed in the workspace.",
                },
                "stdin": {
                    "type": "string",
                    "description": "Optional UTF-8 stdin text for the execution.",
                },
                "timeout_sec": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional execution timeout in seconds.",
                },
                "files": {
                    "type": "array",
                    "description": "Optional inline text files to seed in the workspace.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Relative path within the sandbox workspace.",
                            },
                            "content": {
                                "type": "string",
                                "description": "UTF-8 content written to the file.",
                            },
                        },
                        "required": ["filename", "content"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
}
