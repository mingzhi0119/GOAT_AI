from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tools.desktop.write_desktop_release_provenance import sha256_for_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="write_linux_sidecar_provenance",
        description="Validate one Linux desktop sidecar artifact and write a provenance manifest.",
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--resolved-sha", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target-triple", required=True)
    parser.add_argument("--sbom", default="")
    return parser


def _manifest_path(path: Path, *, cwd: Path) -> str:
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return path.as_posix()


def _artifact_payload(path: Path, *, cwd: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(
            f"Expected Linux desktop artifact at {path}, but it was not created."
        )
    return {
        "path": _manifest_path(path, cwd=cwd),
        "file_name": path.name,
        "sha256": sha256_for_path(path),
        "size_bytes": path.stat().st_size,
    }


def build_provenance_payload(
    *,
    artifact: Path,
    release_ref: str,
    resolved_sha: str,
    platform_label: str,
    target_triple: str,
    cwd: Path,
    sbom: Path | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "release_ref": release_ref,
        "resolved_sha": resolved_sha,
        "platform": platform_label,
        "target_triple": target_triple,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact": _artifact_payload(artifact, cwd=cwd),
    }
    if sbom is not None:
        payload["sbom"] = _artifact_payload(sbom, cwd=cwd)
    return payload


def main() -> None:
    args = _build_parser().parse_args()
    sbom_arg = args.sbom.strip()
    payload = build_provenance_payload(
        artifact=Path(args.artifact).resolve(),
        release_ref=args.release_ref,
        resolved_sha=args.resolved_sha,
        platform_label=args.platform,
        target_triple=args.target_triple,
        cwd=Path.cwd().resolve(),
        sbom=Path(sbom_arg).resolve() if sbom_arg else None,
    )
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output_path.as_posix())


if __name__ == "__main__":
    main()
