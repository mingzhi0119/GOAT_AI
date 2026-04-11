from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services import log_service
from backend.services.workbench_runtime import (
    SQLiteWorkbenchTaskRepository,
    WorkbenchTaskCreatePayload,
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
                auth_scopes=["history:write"],
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
        self.assertEqual([], stored.source_ids)
        self.assertEqual(["history:write"], stored.auth_scopes)
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
                auth_scopes=["history:write"],
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

    def test_list_task_ids_by_status_returns_created_order(self) -> None:
        for task_id, status, created_at in [
            ("wb-queued-1", "queued", "2026-04-10T18:00:01+00:00"),
            ("wb-running-1", "running", "2026-04-10T18:00:02+00:00"),
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


if __name__ == "__main__":
    unittest.main()
