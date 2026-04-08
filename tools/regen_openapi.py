"""Write docs/openapi.json from ``backend.main:app`` (for CI-parity regen with Python 3.12)."""

from __future__ import annotations

import json
from pathlib import Path

from backend.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = REPO_ROOT / "docs" / "openapi.json"


def main() -> None:
    OPENAPI_PATH.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OPENAPI_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
