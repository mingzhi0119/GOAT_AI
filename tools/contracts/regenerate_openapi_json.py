"""Write docs/api/openapi.json from the live FastAPI app (for contract sync).

Run from the repository root::

    python -m tools.contracts.regenerate_openapi_json
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.main import create_contract_app
from tools.contracts._contract_settings import load_contract_settings


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = root / "docs" / "api" / "openapi.json"
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            create_contract_app(load_contract_settings()).openapi(),
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")


if __name__ == "__main__":
    main()
