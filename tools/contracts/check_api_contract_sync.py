"""Verify committed OpenAPI and LLM YAML match the FastAPI app.

Run from the repository root::

    python -m tools.contracts.check_api_contract_sync
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.main import create_contract_app
from tools.contracts._contract_settings import load_contract_settings
from tools.contracts import generate_llm_api_yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "docs" / "api" / "openapi.json"
LLM_API_PATH = REPO_ROOT / "docs" / "api" / "api.llm.yaml"


def main() -> int:
    generated_openapi = create_contract_app(load_contract_settings()).openapi()
    committed_text = OPENAPI_PATH.read_text(encoding="utf-8")
    committed_openapi = json.loads(committed_text)
    # Deep equality: avoids false failures when Python versions emit different dict key order in dumps.
    if generated_openapi != committed_openapi:
        print("Contract check failed: docs/api/openapi.json is out of sync.")
        print("Run: python -m tools.contracts.regenerate_openapi_json")
        print("Then: python -m tools.contracts.generate_llm_api_yaml")
        return 1

    openapi_obj = committed_openapi
    compact = generate_llm_api_yaml._build_compact_spec(openapi_obj)
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_out = Path(tmpdir) / "api.llm.yaml"
        generate_llm_api_yaml._write_yaml(compact, temp_out)
        generated_llm = temp_out.read_text(encoding="utf-8")
    committed_llm = LLM_API_PATH.read_text(encoding="utf-8")
    if generated_llm != committed_llm:
        print("Contract check failed: docs/api/api.llm.yaml is out of sync.")
        print("Run: python -m tools.contracts.generate_llm_api_yaml")
        return 1

    print("API contract artifacts are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
