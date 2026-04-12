from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a normalized security review snapshot from recurring audit evidence."
    )
    parser.add_argument("--pip-audit-json", type=Path, required=True)
    parser.add_argument("--npm-audit-json", type=Path, required=True)
    parser.add_argument("--cargo-audit-json", type=Path, required=True)
    parser.add_argument("--desktop-cargo-exceptions-doc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha", default="")
    parser.add_argument("--ref-name", default="")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-attempt", default="")
    parser.add_argument("--workflow-name", default="quality-trends")
    parser.add_argument("--pip-exit-code", type=int, default=0)
    parser.add_argument("--npm-exit-code", type=int, default=0)
    parser.add_argument("--cargo-exit-code", type=int, default=0)
    parser.add_argument("--shared-api-key-rotated-at", default="")
    parser.add_argument("--deploy-credential-rotated-at", default="")
    parser.add_argument("--desktop-signing-key-rotated-at", default="")
    return parser


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_pip_audit(path: Path) -> dict[str, object]:
    payload = _load_json(path)
    vulnerability_ids: list[str] = []
    if isinstance(payload, list):
        for dependency in payload:
            if not isinstance(dependency, dict):
                continue
            vulns = dependency.get("vulns", [])
            if not isinstance(vulns, list):
                continue
            for vuln in vulns:
                if isinstance(vuln, dict):
                    vuln_id = vuln.get("id")
                    if isinstance(vuln_id, str):
                        vulnerability_ids.append(vuln_id)
    elif isinstance(payload, dict):
        dependencies = payload.get("dependencies", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not isinstance(dependency, dict):
                    continue
                vulns = dependency.get("vulns", [])
                if not isinstance(vulns, list):
                    continue
                for vuln in vulns:
                    if isinstance(vuln, dict):
                        vuln_id = vuln.get("id")
                        if isinstance(vuln_id, str):
                            vulnerability_ids.append(vuln_id)
    unique_ids = sorted(set(vulnerability_ids))
    return {
        "vulnerability_count": len(vulnerability_ids),
        "vulnerability_ids": unique_ids,
    }


def parse_npm_audit(path: Path) -> dict[str, object]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("npm audit JSON must be an object.")
    metadata = payload.get("metadata", {})
    vulnerability_meta = {}
    if isinstance(metadata, dict):
        vulnerability_meta = metadata.get("vulnerabilities", {})
    severity_counts = {
        "info": 0,
        "low": 0,
        "moderate": 0,
        "high": 0,
        "critical": 0,
        "total": 0,
    }
    if isinstance(vulnerability_meta, dict):
        for key in severity_counts:
            severity_counts[key] = int(vulnerability_meta.get(key, 0) or 0)
    advisory_ids: set[str] = set()
    vulnerabilities = payload.get("vulnerabilities", {})
    if isinstance(vulnerabilities, dict):
        for package_data in vulnerabilities.values():
            if not isinstance(package_data, dict):
                continue
            via_items = package_data.get("via", [])
            if not isinstance(via_items, list):
                continue
            for item in via_items:
                if isinstance(item, dict):
                    source = item.get("source")
                    if source is not None:
                        advisory_ids.add(str(source))
    return {
        "severity_counts": severity_counts,
        "vulnerability_count": severity_counts["total"],
        "advisory_ids": sorted(advisory_ids),
    }


def parse_cargo_audit(path: Path) -> dict[str, object]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("cargo audit JSON must be an object.")
    vulnerabilities = payload.get("vulnerabilities", {})
    vulnerability_list = []
    if isinstance(vulnerabilities, dict):
        raw_list = vulnerabilities.get("list", [])
        if isinstance(raw_list, list):
            vulnerability_list = raw_list
    advisory_ids: list[str] = []
    for item in vulnerability_list:
        if not isinstance(item, dict):
            continue
        advisory = item.get("advisory", {})
        if isinstance(advisory, dict):
            advisory_id = advisory.get("id")
            if isinstance(advisory_id, str):
                advisory_ids.append(advisory_id)
    return {
        "vulnerability_count": len(vulnerability_list),
        "advisory_ids": sorted(set(advisory_ids)),
    }


def parse_cargo_exception_doc(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    last_reviewed = re.search(r"Last reviewed:\s*(\d{4}-\d{2}-\d{2})", text)
    review_again_by = re.search(r"Review again by:\s*(\d{4}-\d{2}-\d{2})", text)
    ignored_ids = sorted(set(re.findall(r"RUSTSEC-\d{4}-\d{4}", text)))
    return {
        "last_reviewed": last_reviewed.group(1) if last_reviewed else "",
        "review_again_by": review_again_by.group(1) if review_again_by else "",
        "ignored_ids": ignored_ids,
        "ignored_count": len(ignored_ids),
    }


def _rotation_entry(
    *, credential_class: str, rotated_at: str, today: date
) -> dict[str, object]:
    if not rotated_at.strip():
        return {
            "credential_class": credential_class,
            "rotated_at": "",
            "age_days": None,
            "status": "missing",
        }
    rotated = date.fromisoformat(rotated_at)
    age_days = (today - rotated).days
    return {
        "credential_class": credential_class,
        "rotated_at": rotated.isoformat(),
        "age_days": age_days,
        "status": "ok" if age_days <= 90 else "overdue",
    }


def build_snapshot(
    *,
    pip_audit_json: Path,
    npm_audit_json: Path,
    cargo_audit_json: Path,
    desktop_cargo_exceptions_doc: Path,
    sha: str,
    ref_name: str,
    event_name: str,
    run_id: str,
    run_attempt: str,
    workflow_name: str,
    pip_exit_code: int,
    npm_exit_code: int,
    cargo_exit_code: int,
    shared_api_key_rotated_at: str,
    deploy_credential_rotated_at: str,
    desktop_signing_key_rotated_at: str,
) -> dict[str, object]:
    today = datetime.now(timezone.utc).date()
    pip_summary = parse_pip_audit(pip_audit_json)
    npm_summary = parse_npm_audit(npm_audit_json)
    cargo_summary = parse_cargo_audit(cargo_audit_json)
    cargo_exceptions = parse_cargo_exception_doc(desktop_cargo_exceptions_doc)
    rotation_entries = [
        _rotation_entry(
            credential_class="shared_api_key",
            rotated_at=shared_api_key_rotated_at,
            today=today,
        ),
        _rotation_entry(
            credential_class="deploy_credential",
            rotated_at=deploy_credential_rotated_at,
            today=today,
        ),
        _rotation_entry(
            credential_class="desktop_signing_key",
            rotated_at=desktop_signing_key_rotated_at,
            today=today,
        ),
    ]
    release_blockers: list[str] = []
    if int(npm_summary["severity_counts"]["critical"]) > 0:  # type: ignore[index]
        release_blockers.append("npm_critical_vulnerabilities")
    if int(npm_summary["severity_counts"]["high"]) > 0:  # type: ignore[index]
        release_blockers.append("npm_high_vulnerabilities")
    if int(pip_summary["vulnerability_count"]) > 0:
        release_blockers.append("python_vulnerability_backlog")
    if int(cargo_summary["vulnerability_count"]) > 0:
        release_blockers.append("cargo_vulnerability_backlog")
    attention_items = [
        entry["credential_class"]
        for entry in rotation_entries
        if entry["status"] in {"missing", "overdue"}
    ]
    review_status = (
        "pass" if not release_blockers and not attention_items else "attention_needed"
    )
    dependency_backlog_total = (
        int(pip_summary["vulnerability_count"])
        + int(npm_summary["vulnerability_count"])
        + int(cargo_summary["vulnerability_count"])
    )
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
        "audits": {
            "python": {
                **pip_summary,
                "exit_code": pip_exit_code,
            },
            "node": {
                **npm_summary,
                "exit_code": npm_exit_code,
            },
            "cargo": {
                **cargo_summary,
                "exit_code": cargo_exit_code,
                "exceptions": cargo_exceptions,
            },
        },
        "credential_rotation": {
            "max_age_days": 90,
            "credentials": rotation_entries,
        },
        "review": {
            "status": review_status,
            "release_blocker_count": len(release_blockers),
            "release_blockers": release_blockers,
            "attention_count": len(attention_items),
            "attention_items": attention_items,
            "dependency_backlog_total": dependency_backlog_total,
        },
    }


def main() -> None:
    args = _build_parser().parse_args()
    snapshot = build_snapshot(
        pip_audit_json=args.pip_audit_json,
        npm_audit_json=args.npm_audit_json,
        cargo_audit_json=args.cargo_audit_json,
        desktop_cargo_exceptions_doc=args.desktop_cargo_exceptions_doc,
        sha=args.sha,
        ref_name=args.ref_name,
        event_name=args.event_name,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        workflow_name=args.workflow_name,
        pip_exit_code=args.pip_exit_code,
        npm_exit_code=args.npm_exit_code,
        cargo_exit_code=args.cargo_exit_code,
        shared_api_key_rotated_at=args.shared_api_key_rotated_at,
        deploy_credential_rotated_at=args.deploy_credential_rotated_at,
        desktop_signing_key_rotated_at=args.desktop_signing_key_rotated_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
