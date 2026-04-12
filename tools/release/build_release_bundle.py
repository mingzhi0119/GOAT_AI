from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


EXCLUDED_TOP_LEVEL_NAMES = {
    ".git",
    ".venv",
    ".venv314",
    "__pycache__",
    "backups",
    "data",
    "logs",
    "var",
    "node_modules",
}
EXCLUDED_RELATIVE_PREFIXES = (
    Path("frontend/node_modules"),
    Path("frontend/dist-ssr"),
    Path("frontend/src-tauri/binaries"),
    Path("frontend/src-tauri/gen"),
    Path("frontend/src-tauri/target"),
    Path("frontend/src-tauri/.desktop-sidecar-build"),
)
EXCLUDED_FILE_NAMES = {
    ".coverage",
    "chat_logs.db",
    "chat_logs.db-shm",
    "chat_logs.db-wal",
}
EXCLUDED_SUFFIXES = {
    ".log",
    ".pid",
    ".pyc",
    ".pyo",
    ".tsbuildinfo",
}


@dataclass(frozen=True)
class ReleaseManifest:
    release_ref: str
    resolved_sha: str
    actor: str
    generated_at_utc: str
    bundle_filename: str
    bundle_sha256: str
    bundle_size_bytes: int
    frontend_dist_included: bool
    file_count: int

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, sort_keys=True) + "\n"


def _normalized_tarinfo(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = ""
    tarinfo.gname = ""
    tarinfo.mtime = 0
    return tarinfo


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_under_prefix(path: Path, prefix: Path) -> bool:
    return path == prefix or prefix in path.parents


def should_include_path(repo_root: Path, candidate: Path) -> bool:
    relative = candidate.relative_to(repo_root)
    if not relative.parts:
        return False

    if relative.parts[0] in EXCLUDED_TOP_LEVEL_NAMES:
        return False

    if any(part == "__pycache__" for part in relative.parts):
        return False

    if relative.name in EXCLUDED_FILE_NAMES:
        return False

    if any(relative.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
        return False

    return not any(
        _is_under_prefix(relative, prefix) for prefix in EXCLUDED_RELATIVE_PREFIXES
    )


def iter_bundle_files(repo_root: Path) -> list[Path]:
    files = [
        path
        for path in sorted(repo_root.rglob("*"))
        if path.is_file() and should_include_path(repo_root, path)
    ]

    frontend_index = repo_root / "frontend" / "dist" / "index.html"
    if frontend_index not in files:
        raise ValueError(
            "frontend/dist/index.html is required in the release bundle. "
            "Run `cd frontend && npm run build` first."
        )

    return files


def build_release_bundle(
    *,
    repo_root: Path,
    output_bundle: Path,
    output_manifest: Path,
    release_ref: str,
    resolved_sha: str,
    actor: str,
) -> ReleaseManifest:
    repo_root = repo_root.resolve()
    output_bundle = output_bundle.resolve()
    output_manifest = output_manifest.resolve()
    files = iter_bundle_files(repo_root)

    output_bundle.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(output_bundle, "w:gz") as archive:
        for file_path in files:
            archive.add(
                file_path,
                arcname=file_path.relative_to(repo_root).as_posix(),
                recursive=False,
                filter=_normalized_tarinfo,
            )

    manifest = ReleaseManifest(
        release_ref=release_ref,
        resolved_sha=resolved_sha,
        actor=actor,
        generated_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        bundle_filename=output_bundle.name,
        bundle_sha256=_compute_sha256(output_bundle),
        bundle_size_bytes=output_bundle.stat().st_size,
        frontend_dist_included=True,
        file_count=len(files),
    )
    output_manifest.write_text(manifest.to_json(), encoding="utf-8")
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an immutable GOAT AI release bundle."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to package (defaults to cwd).",
    )
    parser.add_argument(
        "--output-bundle",
        type=Path,
        required=True,
        help="Path to the output .tar.gz bundle.",
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        required=True,
        help="Path to the output release manifest JSON.",
    )
    parser.add_argument("--release-ref", required=True, help="Requested release ref.")
    parser.add_argument("--resolved-sha", required=True, help="Resolved commit SHA.")
    parser.add_argument(
        "--actor",
        default="local",
        help="Actor generating the bundle (GitHub actor or local user label).",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    manifest = build_release_bundle(
        repo_root=args.repo_root,
        output_bundle=args.output_bundle,
        output_manifest=args.output_manifest,
        release_ref=args.release_ref,
        resolved_sha=args.resolved_sha,
        actor=args.actor,
    )
    print(manifest.to_json().strip())


if __name__ == "__main__":
    main()
