from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from backend.services.workbench_source_catalog import (
    WorkbenchSourceDescriptor,
    build_visible_source_facts,
    build_workbench_source_catalog,
)
from goat_ai.config.settings import Settings


def _settings(root: Path) -> Settings:
    return Settings(
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
        ready_skip_ollama_probe=True,
    )


class WorkbenchSourceCatalogTests(unittest.TestCase):
    def test_build_catalog_marks_readonly_sources_unavailable_when_langgraph_disabled(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(
                _settings(Path(tmp)),
                workbench_langgraph_enabled=False,
                workbench_connector_bindings_json="""
                [
                  {
                    "source_id": "connector:ops-runbook",
                    "display_name": "Ops Runbook",
                    "documents": [
                      {
                        "document_id": "connector://ops/runbook",
                        "title": "Ops Runbook",
                        "content": "Incident response and escalation guidance."
                      }
                    ]
                  }
                ]
                """,
            )
            catalog = build_workbench_source_catalog(settings)

        self.assertEqual(
            ["web", "knowledge", "project_memory", "connector:ops-runbook"],
            [descriptor.source_id for descriptor in catalog],
        )
        self.assertIsNone(catalog[1].deny_reason)
        self.assertFalse(catalog[2].runtime_ready)
        self.assertEqual("disabled_by_operator", catalog[2].deny_reason)
        self.assertTrue(catalog[2].requires_project_id)
        self.assertFalse(catalog[3].runtime_ready)
        self.assertEqual("disabled_by_operator", catalog[3].deny_reason)
        self.assertEqual("connector", catalog[3].kind)

    def test_visible_source_facts_only_count_runnable_sources(self) -> None:
        facts = build_visible_source_facts(
            [
                WorkbenchSourceDescriptor(
                    source_id="web",
                    display_name="Public Web",
                    kind="builtin",
                    scope_kind="global",
                    capabilities=("search", "citations"),
                    task_kinds=("browse", "deep_research"),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="Public web search",
                ),
                WorkbenchSourceDescriptor(
                    source_id="project_memory",
                    display_name="Project Memory",
                    kind="project_memory",
                    scope_kind="project_scope",
                    capabilities=("search", "citations"),
                    task_kinds=("browse", "deep_research"),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="Project-scoped retrieval",
                    requires_project_id=True,
                ),
                WorkbenchSourceDescriptor(
                    source_id="connector:ops",
                    display_name="Ops",
                    kind="connector",
                    scope_kind="connector_binding",
                    capabilities=("search",),
                    task_kinds=("browse",),
                    read_only=True,
                    runtime_ready=False,
                    deny_reason="not_implemented",
                    description="Hidden until runtime is ready",
                ),
            ]
        )

        self.assertTrue(facts.has_runnable_task_kind("browse"))
        self.assertTrue(facts.has_runnable_task_kind("deep_research"))
        self.assertTrue(facts.has_runnable_source_id("project_memory"))
        self.assertFalse(facts.has_runnable_source_id("connector:ops"))
        self.assertFalse(facts.has_runnable_source_kind("connector"))


if __name__ == "__main__":
    unittest.main()
