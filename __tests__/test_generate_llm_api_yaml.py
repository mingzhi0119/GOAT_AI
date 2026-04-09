from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import generate_llm_api_yaml


class GenerateLlmApiYamlTests(unittest.TestCase):
    def test_build_compact_spec_includes_expected_endpoints(self) -> None:
        openapi = generate_llm_api_yaml._load_openapi(
            generate_llm_api_yaml.OPENAPI_PATH
        )

        compact = generate_llm_api_yaml._build_compact_spec(openapi)

        self.assertEqual("llm-compact-api", compact["format"])
        self.assertEqual("3.2.0", compact["source"]["openapi_version"])
        ops = {item["op"]: item for item in compact["endpoints"]}
        self.assertIn("chat_stream", ops)
        self.assertIn("analyze_upload_json_route", ops)
        self.assertEqual("/upload/analyze", ops["analyze_upload_json_route"]["path"])
        self.assertEqual(
            "UploadAnalysisResponse",
            ops["analyze_upload_json_route"]["response"]["200"],
        )

    def test_write_yaml_outputs_expected_header(self) -> None:
        document = {
            "format": "llm-compact-api",
            "source": {"canonical_openapi": "docs/openapi.json"},
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "api.llm.yaml"
            generate_llm_api_yaml._write_yaml(document, path)
            text = path.read_text(encoding="utf-8")

        self.assertIn("format: llm-compact-api", text)
        self.assertIn("canonical_openapi: docs/openapi.json", text)


if __name__ == "__main__":
    unittest.main()
