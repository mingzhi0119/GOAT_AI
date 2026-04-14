"""Black-box tests for Phase 15.5 AuthZ: scoped API keys and session ownership."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
import io
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]

from backend.api_errors import (
    AUTH_INVALID_ACCESS_PASSWORD,
    AUTH_LOGIN_REQUIRED,
    AUTH_SESSION_OWNER_REQUIRED,
    AUTH_WRITE_KEY_REQUIRED,
    FEATURE_DISABLED,
    FEATURE_UNAVAILABLE,
)
from __tests__.helpers.api_contract import (
    ContractFakeLLM,
    FakeTitleGenerator,
    parse_sse_payloads,
)
from goat_ai.config.settings import Settings

if TestClient is not None:
    from backend.platform.config import get_settings
    from backend.platform.dependencies import (
        get_code_sandbox_execution_dispatcher,
        get_code_sandbox_provider,
        get_llm_client,
        get_title_generator,
        get_workbench_task_dispatcher,
    )
    from backend.main import create_app
    from backend.models.chat import ChatMessage
    from backend.services.code_sandbox_provider import (
        SandboxProviderRequest,
        SandboxProviderResult,
    )
    from backend.services import log_service
    from backend.services.browser_access_session import hash_shared_access_password
    from backend.services.session_message_codec import (
        SESSION_PAYLOAD_VERSION,
        build_session_payload,
    )


class AuthzFakeCodeSandboxProvider:
    provider_name = "fake-docker"

    def run_stream(self, request: SandboxProviderRequest, *, cancel_requested=None):
        _ = request
        _ = cancel_requested
        yield SandboxProviderResult(
            provider_name=self.provider_name,
            exit_code=0,
            stdout="sandbox ok",
            stderr="",
            timed_out=False,
            cancelled=False,
            error_detail=None,
            output_files=[],
        )


class AuthzNoopCodeSandboxDispatcher:
    def dispatch_execution(self, *, execution_id: str, request_id: str = "") -> None:
        _ = (execution_id, request_id)


class AuthzNoopWorkbenchTaskDispatcher:
    def dispatch_task(self, *, task_id: str, request_id: str = "") -> None:
        _ = (task_id, request_id)


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiAuthzTests(unittest.TestCase):
    def assert_workbench_feature_state(
        self,
        workbench: dict[str, object],
        feature_name: str,
        *,
        allowed_by_config: bool,
        available_on_host: bool,
        effective_enabled: bool,
        deny_reason: str | None,
    ) -> None:
        self.assertEqual(
            {
                "allowed_by_config": allowed_by_config,
                "available_on_host": available_on_host,
                "effective_enabled": effective_enabled,
                "deny_reason": deny_reason,
            },
            {
                "allowed_by_config": workbench[feature_name]["allowed_by_config"],
                "available_on_host": workbench[feature_name]["available_on_host"],
                "effective_enabled": workbench[feature_name]["effective_enabled"],
                "deny_reason": workbench[feature_name]["deny_reason"],
            },
        )

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test system prompt",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            data_dir=root / "data",
            object_store_root=root / "object-store",
            api_key="read-key",
            api_key_write="write-key",
            rate_limit_window_sec=60,
            rate_limit_max_requests=1000,
            ready_skip_ollama_probe=True,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_read_key_forbidden_on_post_chat(self) -> None:
        headers = {"X-GOAT-API-Key": "read-key"}
        response = self.client.post(
            "/api/chat",
            headers=headers,
            json={
                "model": "blackbox-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        self.assertEqual(403, response.status_code)
        body = response.json()
        self.assertEqual(AUTH_WRITE_KEY_REQUIRED, body["code"])

    def test_read_key_allows_get_history(self) -> None:
        headers = {"X-GOAT-API-Key": "read-key"}
        response = self.client.get("/api/history", headers=headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"sessions": []}, response.json())

    def test_require_session_owner_chat_without_header_returns_403(self) -> None:
        self.settings = replace(self.settings, require_session_owner=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        headers = {"X-GOAT-API-Key": "write-key"}
        response = self.client.post(
            "/api/chat",
            headers=headers,
            json={
                "model": "blackbox-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(AUTH_SESSION_OWNER_REQUIRED, response.json()["code"])

    def test_owner_mismatch_returns_404_on_history_get(self) -> None:
        ts = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        payload = build_session_payload(
            messages=[ChatMessage(role="user", content="hi")],
            assistant_text="yo",
            chart_spec=None,
            knowledge_documents=None,
            chart_data_source="none",
        )
        log_service.upsert_session(
            db_path=self.settings.log_db_path,
            session_id="sess-authz-1",
            title="T",
            model="m",
            schema_version=SESSION_PAYLOAD_VERSION,
            payload=payload,
            created_at=ts,
            updated_at=ts,
            owner_id="alice",
        )
        headers = {"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"}
        response = self.client.get("/api/history/sess-authz-1", headers=headers)
        self.assertEqual(404, response.status_code)

    def test_read_key_forbidden_on_knowledge_upload(self) -> None:
        response = self.client.post(
            "/api/knowledge/uploads",
            headers={"X-GOAT-API-Key": "read-key"},
            files={"file": ("notes.txt", io.BytesIO(b"alpha"), "text/plain")},
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(AUTH_WRITE_KEY_REQUIRED, response.json()["code"])

    def test_knowledge_owner_mismatch_returns_404(self) -> None:
        upload = self.client.post(
            "/api/knowledge/uploads",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            files={"file": ("notes.txt", io.BytesIO(b"alpha beta"), "text/plain")},
        )
        self.assertEqual(200, upload.status_code)
        document_id = upload.json()["document_id"]

        response = self.client.get(
            f"/api/knowledge/uploads/{document_id}",
            headers={"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, response.status_code)

    def test_media_owner_mismatch_returns_404_during_chat(self) -> None:
        png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            b"\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
            b"\xe2!\xbc3"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload = self.client.post(
            "/api/media/uploads",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            files={"file": ("tiny.png", io.BytesIO(png), "image/png")},
        )
        self.assertEqual(200, upload.status_code)
        attachment_id = upload.json()["attachment_id"]

        response = self.client.post(
            "/api/chat",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
            json={
                "model": "blackbox-model",
                "messages": [{"role": "user", "content": "describe"}],
                "image_attachment_ids": [attachment_id],
            },
        )
        self.assertEqual(404, response.status_code)

    def test_artifact_download_preserves_owner_scoping(self) -> None:
        self.settings = replace(self.settings, require_session_owner=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create = self.client.post(
            "/api/chat",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={
                "model": "blackbox-model",
                "session_id": "artifact-authz-1",
                "messages": [
                    {
                        "role": "user",
                        "content": "Create a downloadable file with a short brief.",
                    }
                ],
            },
        )
        self.assertEqual(200, create.status_code)
        artifact = next(
            event
            for event in parse_sse_payloads(create.text)
            if event.get("type") == "artifact"
        )
        self.assertTrue(artifact["download_url"].startswith("/api/artifacts/"))

        denied = self.client.get(
            artifact["download_url"],
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, denied.status_code)

        allowed = self.client.get(
            artifact["download_url"],
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
        )
        self.assertEqual(200, allowed.status_code)
        self.assertEqual(
            'attachment; filename="brief.md"',
            allowed.headers["content-disposition"],
        )

    def test_workbench_owner_mismatch_returns_404(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create = self.client.post(
            "/api/workbench/tasks",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={"task_kind": "plan", "prompt": "Draft a plan"},
        )
        self.assertEqual(202, create.status_code)
        task_id = create.json()["task_id"]

        response = self.client.get(
            f"/api/workbench/tasks/{task_id}",
            headers={"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, response.status_code)

        events_response = self.client.get(
            f"/api/workbench/tasks/{task_id}/events",
            headers={"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, events_response.status_code)

    def test_workbench_cancel_owner_mismatch_returns_404(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_workbench_task_dispatcher] = lambda: (
            AuthzNoopWorkbenchTaskDispatcher()
        )

        create = self.client.post(
            "/api/workbench/tasks",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={"task_kind": "plan", "prompt": "Draft a plan"},
        )
        self.assertEqual(202, create.status_code)
        task_id = create.json()["task_id"]

        cancel = self.client.post(
            f"/api/workbench/tasks/{task_id}/cancel",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, cancel.status_code)

    def test_workbench_retry_owner_mismatch_returns_404(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create = self.client.post(
            "/api/workbench/tasks",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={"task_kind": "plan", "prompt": "Draft a plan"},
        )
        self.assertEqual(202, create.status_code)
        task_id = create.json()["task_id"]

        status = self.client.get(
            f"/api/workbench/tasks/{task_id}",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
        )
        self.assertEqual(200, status.status_code)

        retry = self.client.post(
            f"/api/workbench/tasks/{task_id}/retry",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, retry.status_code)

    def test_workbench_workspace_output_owner_mismatch_returns_404(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create = self.client.post(
            "/api/workbench/tasks",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={
                "task_kind": "canvas",
                "prompt": "Draft a canvas",
                "session_id": "sess-output-authz",
            },
        )
        self.assertEqual(202, create.status_code)
        task_id = create.json()["task_id"]
        task_status = self.client.get(
            f"/api/workbench/tasks/{task_id}",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
        )
        self.assertEqual(200, task_status.status_code)
        output_id = task_status.json()["workspace_outputs"][0]["output_id"]

        response = self.client.get(
            f"/api/workbench/workspace-outputs/{output_id}",
            headers={"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, response.status_code)

        export_response = self.client.post(
            f"/api/workbench/workspace-outputs/{output_id}/exports",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
            json={"format": "markdown"},
        )
        self.assertEqual(404, export_response.status_code)

        history_response = self.client.get(
            "/api/history/sess-output-authz",
            headers={"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, history_response.status_code)

    def test_workbench_sources_hide_knowledge_without_knowledge_read_scope(
        self,
    ) -> None:
        self.settings = replace(
            self.settings,
            feature_agent_workbench_enabled=True,
            api_key="bootstrap-auth-enabled",
            api_key_write="",
            api_credentials_json="""
            [
              {
                "credential_id": "cred-workbench-limited",
                "secret": "limited-workbench",
                "principal_id": "principal:limited-workbench",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read"]
              }
            ]
            """,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        response = self.client.get(
            "/api/workbench/sources",
            headers={"X-GOAT-API-Key": "limited-workbench"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            ["web", "project_memory"],
            [item["source_id"] for item in response.json()["sources"]],
        )

        features = self.client.get(
            "/api/system/features",
            headers={"X-GOAT-API-Key": "limited-workbench"},
        )
        self.assertEqual(200, features.status_code)
        workbench = features.json()["workbench"]
        self.assert_workbench_feature_state(
            workbench,
            "agent_tasks",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            workbench,
            "browse",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            workbench,
            "deep_research",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            workbench,
            "artifact_workspace",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            workbench,
            "artifact_exports",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            workbench,
            "project_memory",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            workbench,
            "connectors",
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            deny_reason="permission_denied",
        )

        desktop = self.client.get(
            "/api/system/desktop",
            headers={"X-GOAT-API-Key": "limited-workbench"},
        )
        self.assertEqual(200, desktop.status_code)
        self.assertFalse(desktop.json()["desktop_mode"])

    def test_connector_inventory_and_features_are_concealed_per_caller(self) -> None:
        self.settings = replace(
            self.settings,
            feature_agent_workbench_enabled=True,
            api_key="bootstrap-auth-enabled",
            api_key_write="",
            api_credentials_json="""
            [
              {
                "credential_id": "cred-workbench-reader",
                "secret": "workbench-reader",
                "principal_id": "principal:reader",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read"]
              },
              {
                "credential_id": "cred-workbench-writer",
                "secret": "workbench-writer",
                "principal_id": "principal:writer",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read", "workbench:write"]
              }
            ]
            """,
            workbench_connector_bindings_json="""
            [
              {
                "source_id": "connector:ops-runbook",
                "display_name": "Ops Runbook",
                "documents": [
                  {
                    "document_id": "connector://ops/runbook",
                    "title": "Ops Runbook",
                    "content": "Escalation guidance for workbench research."
                  }
                ],
                "principal_ids": ["principal:writer"]
              }
            ]
            """,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        reader_sources = self.client.get(
            "/api/workbench/sources",
            headers={"X-GOAT-API-Key": "workbench-reader"},
        )
        writer_sources = self.client.get(
            "/api/workbench/sources",
            headers={"X-GOAT-API-Key": "workbench-writer"},
        )
        self.assertEqual(200, reader_sources.status_code)
        self.assertEqual(200, writer_sources.status_code)
        self.assertNotIn(
            "connector:ops-runbook",
            {source["source_id"] for source in reader_sources.json()["sources"]},
        )
        self.assertIn(
            "connector:ops-runbook",
            {source["source_id"] for source in writer_sources.json()["sources"]},
        )

        reader_features = self.client.get(
            "/api/system/features",
            headers={"X-GOAT-API-Key": "workbench-reader"},
        )
        writer_features = self.client.get(
            "/api/system/features",
            headers={"X-GOAT-API-Key": "workbench-writer"},
        )
        self.assertEqual(200, reader_features.status_code)
        self.assertEqual(200, writer_features.status_code)
        self.assert_workbench_feature_state(
            reader_features.json()["workbench"],
            "connectors",
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            writer_features.json()["workbench"],
            "connectors",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )

    def test_workbench_routes_require_scope_family(self) -> None:
        self.settings = replace(
            self.settings,
            feature_agent_workbench_enabled=True,
            api_key="bootstrap-auth-enabled",
            api_key_write="",
            api_credentials_json="""
            [
              {
                "credential_id": "cred-no-workbench",
                "secret": "no-workbench",
                "principal_id": "principal:no-workbench",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "history:write"]
              }
            ]
            """,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        sources = self.client.get(
            "/api/workbench/sources",
            headers={"X-GOAT-API-Key": "no-workbench"},
        )
        self.assertEqual(403, sources.status_code)

        create = self.client.post(
            "/api/workbench/tasks",
            headers={"X-GOAT-API-Key": "no-workbench"},
            json={"task_kind": "plan", "prompt": "Draft a plan"},
        )
        self.assertEqual(403, create.status_code)

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_system_features_resolve_policy_gate_per_credential(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        read_features = self.client.get(
            "/api/system/features", headers={"X-GOAT-API-Key": "read-key"}
        )
        self.assertEqual(200, read_features.status_code)
        self.assertFalse(read_features.json()["code_sandbox"]["policy_allowed"])
        self.assertTrue(read_features.json()["code_sandbox"]["effective_enabled"])

        write_features = self.client.get(
            "/api/system/features", headers={"X-GOAT-API-Key": "write-key"}
        )
        self.assertEqual(200, write_features.status_code)
        self.assertTrue(write_features.json()["code_sandbox"]["policy_allowed"])
        self.assertTrue(write_features.json()["code_sandbox"]["effective_enabled"])

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_exec_policy_denial_returns_403(self, _mock: object) -> None:
        self.settings = replace(
            self.settings,
            feature_code_sandbox_enabled=True,
            api_key="bootstrap-auth-enabled",
            api_key_write="",
            api_credentials_json="""
            [
              {
                "credential_id": "cred-limited-write",
                "secret": "limited-write",
                "principal_id": "principal:limited-write",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:write", "history:read"]
              }
            ]
            """,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        response = self.client.post(
            "/api/code-sandbox/exec",
            headers={"X-GOAT-API-Key": "limited-write"},
            json={},
        )
        self.assertEqual(403, response.status_code)
        body = response.json()
        self.assertEqual(FEATURE_DISABLED, body["code"])

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=False)
    def test_code_sandbox_exec_runtime_denial_returns_503_even_for_write_key(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        response = self.client.post(
            "/api/code-sandbox/exec",
            headers={"X-GOAT-API-Key": "write-key"},
            json={},
        )
        self.assertEqual(503, response.status_code)
        body = response.json()
        self.assertEqual(FEATURE_UNAVAILABLE, body["code"])

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_execution_read_owner_mismatch_returns_404(
        self, _mock: object
    ) -> None:
        self.settings = replace(
            self.settings,
            feature_code_sandbox_enabled=True,
            require_session_owner=True,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            AuthzFakeCodeSandboxProvider()
        )

        create_response = self.client.post(
            "/api/code-sandbox/exec",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={"code": "echo sandbox ok"},
        )
        self.assertEqual(200, create_response.status_code)
        execution_id = create_response.json()["execution_id"]

        read_response = self.client.get(
            f"/api/code-sandbox/executions/{execution_id}",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, read_response.status_code)

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_cancel_owner_mismatch_returns_404(
        self, _mock: object
    ) -> None:
        self.settings = replace(
            self.settings,
            feature_code_sandbox_enabled=True,
            require_session_owner=True,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            AuthzFakeCodeSandboxProvider()
        )
        self.client.app.dependency_overrides[get_code_sandbox_execution_dispatcher] = (
            lambda: AuthzNoopCodeSandboxDispatcher()
        )

        create_response = self.client.post(
            "/api/code-sandbox/exec",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={"execution_mode": "async", "code": "echo sandbox ok"},
        )
        self.assertEqual(202, create_response.status_code)
        execution_id = create_response.json()["execution_id"]

        cancel_response = self.client.post(
            f"/api/code-sandbox/executions/{execution_id}/cancel",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, cancel_response.status_code)

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_retry_owner_mismatch_returns_404(self, _mock: object) -> None:
        self.settings = replace(
            self.settings,
            feature_code_sandbox_enabled=True,
            require_session_owner=True,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            AuthzFakeCodeSandboxProvider()
        )

        create_response = self.client.post(
            "/api/code-sandbox/exec",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "alice"},
            json={"code": "echo sandbox ok"},
        )
        self.assertEqual(200, create_response.status_code)
        execution_id = create_response.json()["execution_id"]

        retry_response = self.client.post(
            f"/api/code-sandbox/executions/{execution_id}/retry",
            headers={"X-GOAT-API-Key": "write-key", "X-GOAT-Owner-Id": "bob"},
        )
        self.assertEqual(404, retry_response.status_code)


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class SharedAccessApiAuthzTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test system prompt",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            data_dir=root / "data",
            object_store_root=root / "object-store",
            shared_access_password_hash=hash_shared_access_password("goat-shared"),
            shared_access_session_secret="shared-secret",
            ready_skip_ollama_probe=True,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app, base_url="https://testserver")
        self.other_client = TestClient(app, base_url="https://testserver")

    def tearDown(self) -> None:
        self.client.close()
        self.other_client.close()
        self.tmpdir.cleanup()

    def _login(self, client: TestClient) -> None:
        response = client.post("/api/auth/login", json={"password": "goat-shared"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["authenticated"])

    def test_shared_access_requires_login_for_history(self) -> None:
        session = self.client.get("/api/auth/session")
        self.assertEqual(200, session.status_code)
        self.assertEqual(
            {
                "auth_required": True,
                "authenticated": False,
                "expires_at": None,
            },
            session.json(),
        )
        self.assertEqual("no-store", session.headers["cache-control"])
        self.assertIn("Cookie", session.headers["vary"])

        history = self.client.get("/api/history")
        self.assertEqual(401, history.status_code)
        self.assertEqual(AUTH_LOGIN_REQUIRED, history.json()["code"])
        self.assertEqual("no-store", history.headers["cache-control"])
        self.assertIn("Cookie", history.headers["vary"])

    def test_shared_access_rejects_invalid_password(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"password": "wrong-password"},
        )

        self.assertEqual(401, response.status_code)
        self.assertEqual(AUTH_INVALID_ACCESS_PASSWORD, response.json()["code"])

    def test_shared_access_browser_sessions_isolate_history(self) -> None:
        self._login(self.client)
        self._login(self.other_client)

        first = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "shared-a",
                "messages": [{"role": "user", "content": "hello from a"}],
            },
        )
        second = self.other_client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "shared-b",
                "messages": [{"role": "user", "content": "hello from b"}],
            },
        )
        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)

        first_history = self.client.get("/api/history")
        second_history = self.other_client.get("/api/history")
        self.assertEqual(
            ["shared-a"],
            [item["id"] for item in first_history.json()["sessions"]],
        )
        self.assertEqual(
            ["shared-b"],
            [item["id"] for item in second_history.json()["sessions"]],
        )
        self.assertEqual(404, self.client.get("/api/history/shared-b").status_code)
        self.assertEqual(
            404, self.other_client.get("/api/history/shared-a").status_code
        )

    def test_shared_access_logout_revokes_browser_history_access(self) -> None:
        self._login(self.client)

        logout = self.client.post("/api/auth/logout")
        self.assertEqual(204, logout.status_code)

        history = self.client.get("/api/history")
        session = self.client.get("/api/auth/session")
        self.assertEqual(401, history.status_code)
        self.assertEqual(AUTH_LOGIN_REQUIRED, history.json()["code"])
        self.assertFalse(session.json()["authenticated"])

    def test_shared_access_cookie_scopes_artifact_downloads(self) -> None:
        self._login(self.client)
        self._login(self.other_client)

        create = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "artifact-shared-1",
                "messages": [
                    {
                        "role": "user",
                        "content": "Create a downloadable file with a short brief.",
                    }
                ],
            },
        )
        self.assertEqual(200, create.status_code)
        artifact = next(
            event
            for event in parse_sse_payloads(create.text)
            if event.get("type") == "artifact"
        )

        denied = self.other_client.get(artifact["download_url"])
        allowed = self.client.get(artifact["download_url"])

        self.assertEqual(404, denied.status_code)
        self.assertEqual(200, allowed.status_code)
        self.assertEqual(
            'attachment; filename="brief.md"',
            allowed.headers["content-disposition"],
        )


if __name__ == "__main__":
    unittest.main()
