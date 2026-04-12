from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import check_api_contract_sync


class CheckApiContractSyncTests(unittest.TestCase):
    def test_main_returns_zero_when_artifacts_are_in_sync(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            root = Path(tmpdir)
            openapi_path = root / "openapi.json"
            llm_path = root / "api.llm.yaml"
            openapi_obj = {"openapi": "3.1.0", "paths": {"/api/health": {}}}
            openapi_path.write_text(json.dumps(openapi_obj), encoding="utf-8")
            llm_path.write_text("paths:\n  /api/health: {}\n", encoding="utf-8")

            with (
                patch.object(check_api_contract_sync, "OPENAPI_PATH", openapi_path),
                patch.object(check_api_contract_sync, "LLM_API_PATH", llm_path),
                patch.object(
                    check_api_contract_sync,
                    "create_contract_app",
                    return_value=SimpleNamespace(openapi=lambda: openapi_obj),
                ),
                patch.object(
                    check_api_contract_sync.generate_llm_api_yaml,
                    "_build_compact_spec",
                    return_value={"paths": {"/api/health": {}}},
                ),
                patch.object(
                    check_api_contract_sync.generate_llm_api_yaml,
                    "_write_yaml",
                    side_effect=lambda compact, out: out.write_text(
                        "paths:\n  /api/health: {}\n", encoding="utf-8"
                    ),
                ),
            ):
                status = check_api_contract_sync.main()

        self.assertEqual(0, status)

    def test_main_returns_one_when_openapi_artifact_drifts(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            root = Path(tmpdir)
            openapi_path = root / "openapi.json"
            llm_path = root / "api.llm.yaml"
            openapi_path.write_text(
                json.dumps({"openapi": "3.1.0", "paths": {"/api/health": {}}}),
                encoding="utf-8",
            )
            llm_path.write_text("paths:\n  /api/health: {}\n", encoding="utf-8")

            with (
                patch.object(check_api_contract_sync, "OPENAPI_PATH", openapi_path),
                patch.object(check_api_contract_sync, "LLM_API_PATH", llm_path),
                patch.object(
                    check_api_contract_sync,
                    "create_contract_app",
                    return_value=SimpleNamespace(
                        openapi=lambda: {"openapi": "3.1.0", "paths": {"/api/chat": {}}}
                    ),
                ),
            ):
                status = check_api_contract_sync.main()

        self.assertEqual(1, status)


if __name__ == "__main__":
    unittest.main()
