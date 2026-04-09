"""Write docs/openapi.json from the live FastAPI app (for contract sync).

Run from the repository root::

    python -m tools.regenerate_openapi_json
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    from backend.main import app

    root = Path(__file__).resolve().parent.parent
    out = root / "docs" / "openapi.json"
    out.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
