from __future__ import annotations

import unittest

from backend.services.workbench_capability_surface import (
    build_workbench_feature_payload,
)
from backend.services.workbench_source_catalog import WorkbenchSourceDescriptor
from goat_ai.config.feature_gates import RuntimeFeatureSnapshot


def _source(
    *,
    source_id: str,
    kind: str,
    task_kinds: tuple[str, ...],
    runtime_ready: bool = True,
) -> WorkbenchSourceDescriptor:
    return WorkbenchSourceDescriptor(
        source_id=source_id,
        display_name=source_id,
        kind=kind,
        scope_kind="global",
        capabilities=("search",),
        task_kinds=task_kinds,
        read_only=True,
        runtime_ready=runtime_ready,
        deny_reason=None if runtime_ready else "not_implemented",
        description=source_id,
    )


class WorkbenchCapabilitySurfaceTests(unittest.TestCase):
    def test_build_feature_payload_keeps_read_and_write_capabilities_distinct(
        self,
    ) -> None:
        response = build_workbench_feature_payload(
            snapshot=RuntimeFeatureSnapshot(
                allowed_by_config=True,
                available_on_host=True,
                effective_enabled=True,
                deny_reason=None,
            ),
            workbench_read_allowed=True,
            workbench_write_allowed=False,
            artifact_export_allowed=False,
            visible_sources=[
                _source(
                    source_id="web",
                    kind="builtin",
                    task_kinds=("browse", "deep_research"),
                ),
                _source(
                    source_id="project_memory",
                    kind="project_memory",
                    task_kinds=("browse", "deep_research"),
                ),
                _source(
                    source_id="connector:ops",
                    kind="connector",
                    task_kinds=("browse", "deep_research"),
                ),
            ],
        )

        self.assertFalse(response.agent_tasks.effective_enabled)
        self.assertEqual("permission_denied", response.agent_tasks.deny_reason)
        self.assertFalse(response.browse.effective_enabled)
        self.assertEqual("permission_denied", response.browse.deny_reason)
        self.assertTrue(response.artifact_workspace.effective_enabled)
        self.assertIsNone(response.artifact_workspace.deny_reason)
        self.assertTrue(response.project_memory.effective_enabled)
        self.assertFalse(response.connectors.effective_enabled)
        self.assertEqual("permission_denied", response.connectors.deny_reason)
        self.assertFalse(response.artifact_exports.effective_enabled)

    def test_build_feature_payload_preserves_operator_disable_reason(self) -> None:
        response = build_workbench_feature_payload(
            snapshot=RuntimeFeatureSnapshot(
                allowed_by_config=False,
                available_on_host=False,
                effective_enabled=False,
                deny_reason="disabled_by_operator",
            ),
            workbench_read_allowed=True,
            workbench_write_allowed=True,
            artifact_export_allowed=True,
            visible_sources=[
                _source(
                    source_id="web",
                    kind="builtin",
                    task_kinds=("browse", "deep_research"),
                ),
                _source(
                    source_id="connector:ops",
                    kind="connector",
                    task_kinds=("browse",),
                ),
            ],
        )

        self.assertFalse(response.browse.effective_enabled)
        self.assertEqual("disabled_by_operator", response.browse.deny_reason)
        self.assertFalse(response.connectors.effective_enabled)
        self.assertEqual("disabled_by_operator", response.connectors.deny_reason)


if __name__ == "__main__":
    unittest.main()
