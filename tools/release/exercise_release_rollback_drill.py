"""Exercise artifact-first release promotion and rollback against a scratch project tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from tools.release.install_release_bundle import (
    DEFAULT_PRESERVE_NAMES,
    install_release_bundle,
    load_release_manifest,
)


@dataclass(frozen=True)
class ReleaseRollbackDrillResult:
    project_dir: str
    current_manifest_path: str
    previous_manifest_path: str
    known_good_resolved_sha: str
    candidate_resolved_sha: str
    rolled_back_resolved_sha: str
    rollback_target_resolved_sha: str
    known_good_tree_sha256: str
    rolled_back_tree_sha256: str


def _top_level_manifest_path(project_dir: Path, filename: str) -> Path:
    return project_dir / filename


def _copy_manifest_into_project(
    *,
    project_dir: Path,
    manifest_path: Path,
    cached_previous_manifest_path: Path | None = None,
) -> None:
    current_manifest_path = _top_level_manifest_path(
        project_dir, "release-manifest.json"
    )
    previous_manifest_path = _top_level_manifest_path(
        project_dir, "release-manifest.previous.json"
    )
    if (
        cached_previous_manifest_path is not None
        and cached_previous_manifest_path.exists()
    ):
        shutil.copy2(cached_previous_manifest_path, previous_manifest_path)
    shutil.copy2(manifest_path, current_manifest_path)


def _cache_current_manifest(
    project_dir: Path, cache_dir: Path, name: str
) -> Path | None:
    current_manifest_path = _top_level_manifest_path(
        project_dir, "release-manifest.json"
    )
    if not current_manifest_path.exists():
        return None
    cached_manifest_path = cache_dir / name
    shutil.copy2(current_manifest_path, cached_manifest_path)
    return cached_manifest_path


def _tree_fingerprint(project_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(project_dir)
        if relative.parts and relative.parts[0] in DEFAULT_PRESERVE_NAMES:
            continue
        if relative.name in {"release-manifest.json", "release-manifest.previous.json"}:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def exercise_release_rollback_drill(
    *,
    known_good_bundle: Path,
    known_good_manifest: Path,
    candidate_bundle: Path,
    candidate_manifest: Path,
    project_dir: Path,
) -> ReleaseRollbackDrillResult:
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="goat-release-rollback-manifests-"
    ) as cache_raw:
        cache_dir = Path(cache_raw)

        known_good_payload = install_release_bundle(
            bundle_path=known_good_bundle,
            manifest_path=known_good_manifest,
            project_dir=project_dir,
            expected_sha=str(
                load_release_manifest(known_good_manifest)["resolved_sha"]
            ),
        )
        _copy_manifest_into_project(
            project_dir=project_dir, manifest_path=known_good_manifest
        )
        known_good_tree_sha = _tree_fingerprint(project_dir)

        previous_known_good_manifest = _cache_current_manifest(
            project_dir, cache_dir, "known-good.json"
        )
        candidate_payload = install_release_bundle(
            bundle_path=candidate_bundle,
            manifest_path=candidate_manifest,
            project_dir=project_dir,
            expected_sha=str(load_release_manifest(candidate_manifest)["resolved_sha"]),
        )
        _copy_manifest_into_project(
            project_dir=project_dir,
            manifest_path=candidate_manifest,
            cached_previous_manifest_path=previous_known_good_manifest,
        )

        previous_candidate_manifest = _cache_current_manifest(
            project_dir, cache_dir, "candidate.json"
        )
        install_release_bundle(
            bundle_path=known_good_bundle,
            manifest_path=known_good_manifest,
            project_dir=project_dir,
            expected_sha=str(known_good_payload["resolved_sha"]),
        )
        _copy_manifest_into_project(
            project_dir=project_dir,
            manifest_path=known_good_manifest,
            cached_previous_manifest_path=previous_candidate_manifest,
        )

    current_manifest_path = _top_level_manifest_path(
        project_dir, "release-manifest.json"
    )
    previous_manifest_path = _top_level_manifest_path(
        project_dir, "release-manifest.previous.json"
    )
    current_payload = load_release_manifest(current_manifest_path)
    previous_payload = load_release_manifest(previous_manifest_path)
    rolled_back_tree_sha = _tree_fingerprint(project_dir)

    if rolled_back_tree_sha != known_good_tree_sha:
        raise ValueError(
            "Artifact rollback drill did not restore the known-good project tree bytes."
        )
    if str(current_payload.get("resolved_sha", "")) != str(
        known_good_payload["resolved_sha"]
    ):
        raise ValueError("Current manifest did not return to the known-good release.")
    if str(previous_payload.get("resolved_sha", "")) != str(
        candidate_payload["resolved_sha"]
    ):
        raise ValueError(
            "Previous manifest did not retain the candidate rollback target."
        )

    return ReleaseRollbackDrillResult(
        project_dir=str(project_dir),
        current_manifest_path=str(current_manifest_path),
        previous_manifest_path=str(previous_manifest_path),
        known_good_resolved_sha=str(known_good_payload["resolved_sha"]),
        candidate_resolved_sha=str(candidate_payload["resolved_sha"]),
        rolled_back_resolved_sha=str(current_payload["resolved_sha"]),
        rollback_target_resolved_sha=str(previous_payload["resolved_sha"]),
        known_good_tree_sha256=known_good_tree_sha,
        rolled_back_tree_sha256=rolled_back_tree_sha,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exercise-release-rollback-drill",
        description=(
            "Exercise artifact-first release promotion and rollback against a scratch project tree."
        ),
    )
    parser.add_argument("--known-good-bundle", type=Path, required=True)
    parser.add_argument("--known-good-manifest", type=Path, required=True)
    parser.add_argument("--candidate-bundle", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--project-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = exercise_release_rollback_drill(
        known_good_bundle=args.known_good_bundle,
        known_good_manifest=args.known_good_manifest,
        candidate_bundle=args.candidate_bundle,
        candidate_manifest=args.candidate_manifest,
        project_dir=args.project_dir,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
