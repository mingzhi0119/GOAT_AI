from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services import log_service
from backend.services.workbench_runtime import (
    SQLiteWorkbenchTaskRepository,
    WorkbenchTaskCreatePayload,
    WorkbenchWorkspaceOutputCreatePayload,
)


class WorkbenchRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.tmpdir.name) / "chat_logs.db"
        log_service.init_db(self.db_path)
        self.repository = SQLiteWorkbenchTaskRepository(self.db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_claim_complete_and_get_round_trip(self) -> None:
        created = self.repository.create_task(
            WorkbenchTaskCreatePayload(
                task_id="wb-1",
                task_kind="plan",
                prompt="Draft a plan",
                session_id=None,
                project_id=None,
                knowledge_document_ids=[],
                connector_ids=[],
                source_ids=[],
                created_at="2026-04-10T18:00:00+00:00",
                updated_at="2026-04-10T18:00:00+00:00",
                auth_scopes=["workbench:read", "workbench:write"],
                credential_id="cred-1",
                auth_mode="api_key",
            )
        )
        self.assertEqual("queued", created.status)
        self.assertIsNone(created.result_text)

        claimed = self.repository.claim_task_for_execution(
            "wb-1", updated_at="2026-04-10T18:00:01+00:00"
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual("running", claimed.status)
        self.assertIsNone(
            self.repository.claim_task_for_execution(
                "wb-1", updated_at="2026-04-10T18:00:02+00:00"
            )
        )

        self.repository.mark_task_completed(
            "wb-1",
            updated_at="2026-04-10T18:00:03+00:00",
            result_text="## Goal\n- Draft a plan",
            result_citations=[
                {
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "filename": "notes.md",
                    "snippet": "alpha",
                    "score": 0.9,
                }
            ],
        )
        stored = self.repository.get_task("wb-1")
        assert stored is not None
        self.assertEqual("completed", stored.status)
        self.assertEqual("## Goal\n- Draft a plan", stored.result_text)
        self.assertEqual("doc-1", stored.result_citations[0]["document_id"])
        self.assertEqual([], self.repository.list_workspace_outputs("wb-1"))
        self.assertEqual([], stored.source_ids)
        self.assertEqual(["workbench:read", "workbench:write"], stored.auth_scopes)
        self.assertEqual("cred-1", stored.credential_id)
        self.assertIsNone(stored.error_detail)
        events = self.repository.list_task_events("wb-1")
        self.assertEqual(
            ["task.queued", "task.started", "task.completed"],
            [event.event_type for event in events],
        )
        self.assertEqual([1, 2, 3], [event.sequence for event in events])
        self.assertEqual("completed", events[-1].status)
        self.assertEqual("markdown", events[-1].metadata["result_format"])
        self.assertEqual(1, events[-1].metadata["citation_count"])
        self.assertEqual(0, events[-1].metadata["workspace_output_count"])

    def test_create_workspace_output_persists_typed_document(self) -> None:
        self.repository.create_task(
            WorkbenchTaskCreatePayload(
                task_id="wb-canvas",
                task_kind="canvas",
                prompt="Draft a canvas",
                session_id="session-1",
                project_id="project-1",
                knowledge_document_ids=[],
                connector_ids=[],
                source_ids=[],
                created_at="2026-04-10T18:00:00+00:00",
                updated_at="2026-04-10T18:00:00+00:00",
            )
        )
        self.repository.claim_task_for_execution(
            "wb-canvas", updated_at="2026-04-10T18:00:01+00:00"
        )

        created = self.repository.create_workspace_output(
            WorkbenchWorkspaceOutputCreatePayload(
                output_id="wbo-1",
                task_id="wb-canvas",
                output_kind="canvas_document",
                title="Canvas title",
                content_format="markdown",
                content_text="# Canvas title\n\nDraft body",
                created_at="2026-04-10T18:00:02+00:00",
                updated_at="2026-04-10T18:00:02+00:00",
                metadata={"editable": True},
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        )

        self.assertEqual("wbo-1", created.id)
        stored = self.repository.list_workspace_outputs("wb-canvas")
        self.assertEqual(1, len(stored))
        self.assertEqual("canvas_document", stored[0].output_kind)
        self.assertEqual("Canvas title", stored[0].title)
        self.assertEqual("# Canvas title\n\nDraft body", stored[0].content_text)
        self.assertTrue(stored[0].metadata["editable"])
        self.assertEqual(
            "session-1", self.repository.get_workspace_output("wbo-1").session_id
        )
        self.assertEqual(
            ["wbo-1"],
            [
                output.id
                for output in self.repository.list_workspace_outputs_for_session(
                    "session-1"
                )
            ],
        )
        self.assertEqual(
            ["wbo-1"],
            [
                output.id
                for output in self.repository.list_workspace_outputs_for_project(
                    "project-1"
                )
            ],
        )
        self.repository.replace_workspace_output_metadata(
            "wbo-1",
            metadata={
                "editable": True,
                "artifacts": [
                    {
                        "artifact_id": "art-1",
                        "filename": "canvas.md",
                        "mime_type": "text/markdown",
                        "byte_size": 12,
                        "download_url": "/api/artifacts/art-1",
                    }
                ],
            },
            updated_at="2026-04-10T18:00:03+00:00",
        )
        refreshed = self.repository.get_workspace_output("wbo-1")
        assert refreshed is not None
        self.assertEqual("art-1", refreshed.metadata["artifacts"][0]["artifact_id"])

        events = self.repository.list_task_events("wb-canvas")
        self.assertEqual(
            ["task.queued", "task.started", "workspace_output.created"],
            [event.event_type for event in events],
        )
        self.assertEqual("wbo-1", events[-1].metadata["output_id"])

    def test_mark_failed_persists_error_detail(self) -> None:
        self.repository.create_task(
            WorkbenchTaskCreatePayload(
                task_id="wb-2",
                task_kind="plan",
                prompt="Draft a plan",
                session_id=None,
                project_id=None,
                knowledge_document_ids=[],
                connector_ids=[],
                source_ids=[],
                created_at="2026-04-10T18:00:00+00:00",
                updated_at="2026-04-10T18:00:00+00:00",
                auth_scopes=["workbench:read", "workbench:write"],
                credential_id="cred-2",
                auth_mode="api_key",
            )
        )
        self.repository.mark_task_failed(
            "wb-2",
            updated_at="2026-04-10T18:00:03+00:00",
            error_detail="AI backend unavailable.",
        )
        stored = self.repository.get_task("wb-2")
        assert stored is not None
        self.assertEqual("failed", stored.status)
        self.assertEqual("AI backend unavailable.", stored.error_detail)
        self.assertIsNone(stored.result_text)
        events = self.repository.list_task_events("wb-2")
        self.assertEqual(
            ["task.queued", "task.failed"], [event.event_type for event in events]
        )
        self.assertEqual("AI backend unavailable.", events[-1].message)

    def test_mark_cancelled_persists_error_detail(self) -> None:
        self.repository.create_task(
            WorkbenchTaskCreatePayload(
                task_id="wb-cancelled",
                task_kind="plan",
                prompt="Draft a plan",
                session_id=None,
                project_id=None,
                knowledge_document_ids=[],
                connector_ids=[],
                source_ids=[],
                created_at="2026-04-10T18:00:00+00:00",
                updated_at="2026-04-10T18:00:00+00:00",
                auth_scopes=["workbench:read", "workbench:write"],
                credential_id="cred-3",
                auth_mode="api_key",
            )
        )
        self.repository.mark_task_cancelled(
            "wb-cancelled",
            updated_at="2026-04-10T18:00:01+00:00",
            error_detail="Task cancelled before execution.",
        )

        stored = self.repository.get_task("wb-cancelled")
        assert stored is not None
        self.assertEqual("cancelled", stored.status)
        self.assertEqual("Task cancelled before execution.", stored.error_detail)
        self.assertIsNone(stored.result_text)
        events = self.repository.list_task_events("wb-cancelled")
        self.assertEqual(
            ["task.queued", "task.cancelled"],
            [event.event_type for event in events],
        )
        self.assertEqual("cancelled", events[-1].status)

    def test_list_task_ids_by_status_returns_created_order(self) -> None:
        for task_id, status, created_at in [
            ("wb-queued-1", "queued", "2026-04-10T18:00:01+00:00"),
            ("wb-running-1", "running", "2026-04-10T18:00:02+00:00"),
            ("wb-cancelled-1", "cancelled", "2026-04-10T18:00:02.500000+00:00"),
            ("wb-queued-2", "queued", "2026-04-10T18:00:03+00:00"),
        ]:
            self.repository.create_task(
                WorkbenchTaskCreatePayload(
                    task_id=task_id,
                    task_kind="plan",
                    prompt="Draft a plan",
                    session_id=None,
                    project_id=None,
                    knowledge_document_ids=[],
                    connector_ids=[],
                    source_ids=[],
                    created_at=created_at,
                    updated_at=created_at,
                    status=status,
                )
            )

        self.assertEqual(
            ["wb-queued-1", "wb-queued-2"],
            self.repository.list_task_ids_by_status(["queued"]),
        )
        self.assertEqual(
            ["wb-queued-1", "wb-running-1", "wb-queued-2"],
            self.repository.list_task_ids_by_status(["queued", "running"]),
        )
        self.assertEqual(
            ["wb-cancelled-1"],
            self.repository.list_task_ids_by_status(["cancelled"]),
        )


if __name__ == "__main__":
    unittest.main()
