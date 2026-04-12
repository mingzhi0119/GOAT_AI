from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="write_desktop_release_provenance",
        description="Validate packaged desktop artifacts and write release provenance.",
    )
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--pattern", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--resolved-sha", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument(
        "--distribution-channel",
        default="internal_test",
        choices=("public", "internal_test"),
    )
    parser.add_argument("--require-signed", action="store_true")
    return parser


def sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_artifacts(bundle_root: Path, patterns: list[str]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        matches = sorted(path for path in bundle_root.glob(pattern) if path.is_file())
        if not matches:
            raise SystemExit(
                f"Expected packaged desktop artifact matching {pattern!r} under {bundle_root}"
            )
        for match in matches:
            resolved = match.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)
    return discovered


def _signature_shell() -> str:
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell:
        return shell
    raise RuntimeError("Could not locate PowerShell for Authenticode verification.")


def authenticode_status(path: Path) -> str | None:
    if platform.system() != "Windows":
        return None
    escaped_path = str(path).replace("'", "''")
    command = [
        _signature_shell(),
        "-NoProfile",
        "-Command",
        (
            "$signature = Get-AuthenticodeSignature -FilePath "
            f"'{escaped_path}'; "
            "Write-Output $signature.Status"
        ),
    ]
    completed = subprocess.run(  # noqa: S603
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "Unknown"


def _manifest_path(path: Path, *, cwd: Path) -> str:
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return path.as_posix()


def build_provenance_payload(
    *,
    bundle_root: Path,
    patterns: list[str],
    release_ref: str,
    resolved_sha: str,
    platform_label: str,
    distribution_channel: str,
    require_signed: bool,
    cwd: Path,
) -> dict[str, object]:
    artifacts = discover_artifacts(bundle_root, patterns)
    payload_artifacts: list[dict[str, object]] = []
    for artifact in artifacts:
        signature_status = authenticode_status(artifact)
        signed = signature_status == "Valid" if signature_status is not None else None
        if require_signed and signed is not True:
            raise SystemExit(
                f"Expected signed desktop artifact but {artifact.name} had "
                f"signature status {signature_status or 'unavailable'}."
            )
        payload_artifacts.append(
            {
                "path": _manifest_path(artifact, cwd=cwd),
                "file_name": artifact.name,
                "sha256": sha256_for_path(artifact),
                "size_bytes": artifact.stat().st_size,
                "signature_status": signature_status,
                "signed": signed,
            }
        )

    return {
        "release_ref": release_ref,
        "resolved_sha": resolved_sha,
        "platform": platform_label,
        "distribution_channel": distribution_channel,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifacts": payload_artifacts,
    }


def main() -> None:
    args = _build_parser().parse_args()
    payload = build_provenance_payload(
        bundle_root=Path(args.bundle_root).resolve(),
        patterns=list(args.pattern),
        release_ref=args.release_ref,
        resolved_sha=args.resolved_sha,
        platform_label=args.platform,
        distribution_channel=args.distribution_channel,
        require_signed=args.require_signed,
        cwd=Path.cwd().resolve(),
    )
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output_path.as_posix())


if __name__ == "__main__":
    main()
