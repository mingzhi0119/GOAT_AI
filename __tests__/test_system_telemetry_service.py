from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.services.system_telemetry_service import (
    build_runtime_target_response,
    build_system_features_response,
)
from goat_ai.config import Settings
from goat_ai.feature_gates import CodeSandboxFeatureSnapshot, RuntimeFeatureSnapshot


def _settings() -> Settings:
    root = Path(tempfile.gettempdir()) / "goat-ai-telemetry-tests"
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
    )


def _auth_context() -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal-1"),
        tenant_id=TenantId("tenant-1"),
        scopes=frozenset({"sandbox:execute", "knowledge:read"}),
        credential_id="cred-1",
        legacy_owner_id="owner-1",
        auth_mode="api_key",
    )


class SystemTelemetryServiceTests(unittest.TestCase):
    def test_builds_workbench_feature_flags_from_runnable_sources(self) -> None:
        with (
            patch(
                "backend.services.system_telemetry_service.compute_code_sandbox_snapshot",
                return_value=CodeSandboxFeatureSnapshot(
                    allowed_by_config=True,
                    available_on_host=True,
                    effective_enabled=True,
                    provider_name="docker",
                    isolation_level="container",
                    network_policy_enforced=True,
                    deny_reason=None,
                ),
            ),
            patch(
                "backend.services.system_telemetry_service.compute_agent_workbench_snapshot",
                return_value=RuntimeFeatureSnapshot(
                    allowed_by_config=True,
                    available_on_host=True,
                    effective_enabled=True,
                    deny_reason=None,
                ),
            ),
            patch(
                "backend.services.system_telemetry_service.code_sandbox_policy_allowed",
                return_value=True,
            ),
            patch(
                "backend.services.system_telemetry_service.list_workbench_sources",
                return_value=[
                    type(
                        "Source",
                        (),
                        {
                            "runtime_ready": True,
                            "task_kinds": ["browse", "deep_research"],
                            "kind": "connector",
                        },
                    )(),
                    type(
                        "Source",
                        (),
                        {
                            "runtime_ready": False,
                            "task_kinds": ["browse"],
                            "kind": "knowledge_base",
                        },
                    )(),
                ],
            ),
        ):
            response = build_system_features_response(_settings(), _auth_context())

        self.assertTrue(response.code_sandbox.policy_allowed)
        self.assertTrue(response.workbench.browse.effective_enabled)
        self.assertTrue(response.workbench.deep_research.effective_enabled)
        self.assertTrue(response.workbench.artifact_workspace.effective_enabled)
        self.assertIsNone(response.workbench.artifact_workspace.deny_reason)
        self.assertTrue(response.workbench.connectors.effective_enabled)

    def test_preserves_operator_disabled_workbench_snapshot(self) -> None:
        with (
            patch(
                "backend.services.system_telemetry_service.compute_code_sandbox_snapshot",
                return_value=CodeSandboxFeatureSnapshot(
                    allowed_by_config=False,
                    available_on_host=False,
                    effective_enabled=False,
                    provider_name="docker",
                    isolation_level="container",
                    network_policy_enforced=True,
                    deny_reason="disabled_by_operator",
                ),
            ),
            patch(
                "backend.services.system_telemetry_service.compute_agent_workbench_snapshot",
                return_value=RuntimeFeatureSnapshot(
                    allowed_by_config=False,
                    available_on_host=False,
                    effective_enabled=False,
                    deny_reason="disabled_by_operator",
                ),
            ),
            patch(
                "backend.services.system_telemetry_service.code_sandbox_policy_allowed",
                return_value=False,
            ),
            patch(
                "backend.services.system_telemetry_service.list_workbench_sources",
                return_value=[],
            ),
        ):
            response = build_system_features_response(_settings(), _auth_context())

        self.assertFalse(response.code_sandbox.effective_enabled)
        self.assertEqual("disabled_by_operator", response.workbench.browse.deny_reason)
        self.assertFalse(response.workbench.connectors.effective_enabled)

    def test_runtime_target_response_exposes_single_instance_contract(self) -> None:
        response = build_runtime_target_response(_settings())

        self.assertEqual("sqlite-first", response.operational_contract.storage_model)
        self.assertEqual(
            "single-writer", response.operational_contract.concurrency_model
        )
        self.assertIn(
            "rate_limiting", response.operational_contract.process_local_seams
        )
        self.assertIn(
            "background_jobs", response.operational_contract.process_local_seams
        )
        self.assertIn(
            "latency_metrics", response.operational_contract.process_local_seams
        )


if __name__ == "__main__":
    unittest.main()
