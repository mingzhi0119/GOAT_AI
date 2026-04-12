from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path


DEFAULT_PRESERVE_NAMES = {
    ".env",
    ".git",
    ".venv",
    ".venv314",
    "backups",
    "chat_logs.db",
    "chat_logs.db-shm",
    "chat_logs.db-wal",
    "data",
    "logs",
}


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_release_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Release manifest must be a JSON object.")
    return payload


def validate_release_artifacts(
    *,
    bundle_path: Path,
    manifest_path: Path,
    expected_sha: str = "",
) -> dict[str, object]:
    manifest = load_release_manifest(manifest_path)
    manifest_sha = str(manifest.get("resolved_sha", "")).strip()
    if not manifest_sha:
        raise ValueError("Release manifest is missing resolved_sha.")
    if expected_sha and manifest_sha != expected_sha:
        raise ValueError(
            f"Release manifest SHA {manifest_sha} did not match EXPECTED_GIT_SHA {expected_sha}."
        )

    manifest_digest = str(manifest.get("bundle_sha256", "")).strip()
    actual_digest = _compute_sha256(bundle_path)
    if not manifest_digest:
        raise ValueError("Release manifest is missing bundle_sha256.")
    if manifest_digest != actual_digest:
        raise ValueError(
            f"Release bundle digest {actual_digest} did not match manifest digest {manifest_digest}."
        )
    return manifest


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink(missing_ok=True)


def _copy_entry(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _sync_project_tree(
    *,
    source_root: Path,
    project_dir: Path,
    preserve_names: set[str],
) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)

    for child in project_dir.iterdir():
        if child.name in preserve_names:
            continue
        _remove_path(child)

    for child in source_root.iterdir():
        if child.name in preserve_names:
            continue
        _copy_entry(child, project_dir / child.name)


def install_release_bundle(
    *,
    bundle_path: Path,
    manifest_path: Path,
    project_dir: Path,
    expected_sha: str = "",
    preserve_names: set[str] | None = None,
) -> dict[str, object]:
    bundle_path = bundle_path.resolve()
    manifest_path = manifest_path.resolve()
    project_dir = project_dir.resolve()
    preserve = set(DEFAULT_PRESERVE_NAMES)
    if preserve_names:
        preserve.update(preserve_names)

    manifest = validate_release_artifacts(
        bundle_path=bundle_path,
        manifest_path=manifest_path,
        expected_sha=expected_sha,
    )

    with tempfile.TemporaryDirectory(prefix="goat-release-bundle-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        with tarfile.open(bundle_path, "r:gz") as archive:
            archive.extractall(temp_dir)
        _sync_project_tree(
            source_root=temp_dir,
            project_dir=project_dir,
            preserve_names=preserve,
        )

    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install a GOAT AI release bundle.")
    parser.add_argument(
        "--bundle", type=Path, required=True, help="Path to the bundle tar.gz."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to the release manifest JSON.",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Target project directory to replace.",
    )
    parser.add_argument(
        "--expected-sha",
        default="",
        help="Optional SHA that the release manifest must match.",
    )
    parser.add_argument(
        "--preserve",
        action="append",
        default=[],
        help="Extra top-level names to preserve in the target project directory.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    install_release_bundle(
        bundle_path=args.bundle,
        manifest_path=args.manifest,
        project_dir=args.project_dir,
        expected_sha=args.expected_sha,
        preserve_names=set(args.preserve),
    )
    print(json.dumps({"installed": True, "project_dir": str(args.project_dir)}))


if __name__ == "__main__":
    main()
