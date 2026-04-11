from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a normalized JSON snapshot for recurring quality-trend workflows."
    )
    parser.add_argument("--backend-coverage-json", type=Path, required=True)
    parser.add_argument("--frontend-lcov", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha", default="")
    parser.add_argument("--ref-name", default="")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-attempt", default="")
    parser.add_argument("--workflow-name", default="quality-trends")
    return parser


def _percent(hit: int, found: int) -> float | None:
    if found <= 0:
        return None
    return round((hit / found) * 100.0, 2)


def parse_backend_coverage(path: Path) -> dict[str, float | int | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    if not isinstance(totals, dict):
        raise ValueError("Backend coverage JSON is missing a totals object.")

    statements_total = int(totals.get("num_statements", 0) or 0)
    statements_covered = int(totals.get("covered_lines", 0) or 0)
    statements_missing = int(totals.get("missing_lines", 0) or 0)
    statements_pct = float(totals.get("percent_covered", 0.0) or 0.0)

    branches_total = int(totals.get("num_branches", 0) or 0)
    branches_covered = int(totals.get("covered_branches", 0) or 0)
    branches_missing = int(totals.get("missing_branches", 0) or 0)

    return {
        "statements_total": statements_total,
        "statements_covered": statements_covered,
        "statements_missing": statements_missing,
        "statements_pct": round(statements_pct, 2),
        "branches_total": branches_total,
        "branches_covered": branches_covered,
        "branches_missing": branches_missing,
        "branches_pct": _percent(branches_covered, branches_total),
    }


def parse_frontend_lcov(path: Path) -> dict[str, float | int | None]:
    totals = {
        "lines_found": 0,
        "lines_hit": 0,
        "functions_found": 0,
        "functions_hit": 0,
        "branches_found": 0,
        "branches_hit": 0,
    }
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        if key == "LF":
            totals["lines_found"] += int(value or 0)
        elif key == "LH":
            totals["lines_hit"] += int(value or 0)
        elif key == "FNF":
            totals["functions_found"] += int(value or 0)
        elif key == "FNH":
            totals["functions_hit"] += int(value or 0)
        elif key == "BRF":
            totals["branches_found"] += int(value or 0)
        elif key == "BRH":
            totals["branches_hit"] += int(value or 0)

    return {
        "lines_total": totals["lines_found"],
        "lines_covered": totals["lines_hit"],
        "lines_pct": _percent(totals["lines_hit"], totals["lines_found"]),
        "functions_total": totals["functions_found"],
        "functions_covered": totals["functions_hit"],
        "functions_pct": _percent(totals["functions_hit"], totals["functions_found"]),
        "branches_total": totals["branches_found"],
        "branches_covered": totals["branches_hit"],
        "branches_pct": _percent(totals["branches_hit"], totals["branches_found"]),
    }


def build_snapshot(
    *,
    backend_coverage_json: Path,
    frontend_lcov: Path,
    sha: str,
    ref_name: str,
    event_name: str,
    run_id: str,
    run_attempt: str,
    workflow_name: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow": {
            "name": workflow_name,
            "event_name": event_name,
            "run_id": run_id,
            "run_attempt": run_attempt,
        },
        "git": {
            "sha": sha,
            "ref_name": ref_name,
        },
        "metrics": {
            "backend_coverage": parse_backend_coverage(backend_coverage_json),
            "frontend_coverage": parse_frontend_lcov(frontend_lcov),
        },
    }


def main() -> None:
    args = _build_parser().parse_args()
    snapshot = build_snapshot(
        backend_coverage_json=args.backend_coverage_json,
        frontend_lcov=args.frontend_lcov,
        sha=args.sha,
        ref_name=args.ref_name,
        event_name=args.event_name,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        workflow_name=args.workflow_name,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
