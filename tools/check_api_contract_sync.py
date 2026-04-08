from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ruff: noqa: E402
from backend.main import app
from tools import generate_llm_api_yaml

OPENAPI_PATH = REPO_ROOT / "docs" / "openapi.json"
LLM_API_PATH = REPO_ROOT / "docs" / "api.llm.yaml"


def _normalized_json_text(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    generated_openapi = _normalized_json_text(app.openapi())
    committed_openapi = OPENAPI_PATH.read_text(encoding="utf-8")
    if generated_openapi != committed_openapi:
        print("Contract check failed: docs/openapi.json is out of sync.")
        print(
            "Run: python -c \"import json; from backend.main import app; from pathlib import Path; Path('docs/openapi.json').write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2)+'\\n', encoding='utf-8')\""
        )
        return 1

    openapi_obj = json.loads(committed_openapi)
    compact = generate_llm_api_yaml._build_compact_spec(openapi_obj)
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_out = Path(tmpdir) / "api.llm.yaml"
        generate_llm_api_yaml._write_yaml(compact, temp_out)
        generated_llm = temp_out.read_text(encoding="utf-8")
    committed_llm = LLM_API_PATH.read_text(encoding="utf-8")
    if generated_llm != committed_llm:
        print("Contract check failed: docs/api.llm.yaml is out of sync.")
        print("Run: python tools/generate_llm_api_yaml.py")
        return 1

    print("API contract artifacts are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
