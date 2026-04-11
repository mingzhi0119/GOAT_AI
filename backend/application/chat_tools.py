"""Application-owned executors for chat-native tool calls."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from backend.application.code_sandbox import execute_code_sandbox_request
from backend.application.ports import (
    CodeSandboxExecutionDispatcher,
    CodeSandboxExecutionRepository,
    FeatureNotAvailable,
    SandboxProvider,
    Settings,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.code_sandbox import CodeSandboxExecRequest
from backend.services.feature_gate_service import (
    code_sandbox_policy_allowed,
    get_code_sandbox_snapshot,
)


class ApplicationChatToolExecutor:
    """Run chat-native tools through existing application use cases."""

    def __init__(
        self,
        *,
        sandbox_repository: CodeSandboxExecutionRepository,
        sandbox_provider: SandboxProvider,
        sandbox_dispatcher: CodeSandboxExecutionDispatcher,
        settings: Settings,
    ) -> None:
        self._sandbox_repository = sandbox_repository
        self._sandbox_provider = sandbox_provider
        self._sandbox_dispatcher = sandbox_dispatcher
        self._settings = settings

    def code_sandbox_tool_enabled(
        self,
        *,
        auth_context: AuthorizationContext | None,
    ) -> bool:
        if auth_context is None:
            return False
        snapshot = get_code_sandbox_snapshot(self._settings)
        return snapshot.effective_enabled and code_sandbox_policy_allowed(auth_context)

    def execute_code_sandbox_tool(
        self,
        *,
        arguments: dict[str, Any],
        auth_context: AuthorizationContext | None,
        request_id: str = "",
    ) -> dict[str, object]:
        if auth_context is None:
            return {
                "ok": False,
                "error_type": "authorization",
                "error_detail": "Code sandbox tool requires an authorization context.",
            }

        payload_dict = dict(arguments)
        payload_dict["execution_mode"] = "sync"
        payload_dict["network_policy"] = "disabled"
        try:
            request = CodeSandboxExecRequest.model_validate(payload_dict)
            result = execute_code_sandbox_request(
                request=request,
                repository=self._sandbox_repository,
                provider=self._sandbox_provider,
                dispatcher=self._sandbox_dispatcher,
                settings=self._settings,
                auth_context=auth_context,
            )
        except ValidationError as exc:
            return {
                "ok": False,
                "error_type": "validation",
                "error_detail": str(exc),
            }
        except FeatureNotAvailable as exc:
            return {
                "ok": False,
                "error_type": exc.gate_kind,
                "error_detail": exc.deny_reason,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error_type": "execution",
                "error_detail": str(exc),
            }

        return {
            "ok": True,
            **result.model_dump(mode="json"),
        }
