"""Write docs/openapi.json from the live FastAPI app (for contract sync).

Run from the repository root::

    python -m tools.contracts.regenerate_openapi_json
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.main import create_contract_app


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = root / "docs" / "openapi.json"
    out.write_text(
        json.dumps(create_contract_app().openapi(), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
