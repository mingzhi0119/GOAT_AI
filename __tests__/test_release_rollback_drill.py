from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.exercise_release_rollback_drill import exercise_release_rollback_drill
from tools.build_release_bundle import build_release_bundle
from tools.install_release_bundle import load_release_manifest


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_bundle(
    repo_root: Path, artifacts_root: Path, ref: str, sha: str
) -> tuple[Path, Path]:
    bundle_path = artifacts_root / f"{sha}.tar.gz"
    manifest_path = artifacts_root / f"{sha}.json"
    build_release_bundle(
        repo_root=repo_root,
        output_bundle=bundle_path,
        output_manifest=manifest_path,
        release_ref=ref,
        resolved_sha=sha,
        actor="tester",
    )
    return bundle_path, manifest_path


def test_release_rollback_drill_restores_known_good_bundle_and_manifest_chain() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        known_good_repo = root / "known-good"
        candidate_repo = root / "candidate"
        artifacts_root = root / "artifacts"
        project_dir = root / "project"

        _write(known_good_repo / "deploy.sh", "#!/usr/bin/env bash\n")
        _write(known_good_repo / "backend" / "main.py", "print('known-good')\n")
        _write(
            known_good_repo / "frontend" / "dist" / "index.html", "<!doctype html>\n"
        )

        _write(candidate_repo / "deploy.sh", "#!/usr/bin/env bash\n")
        _write(candidate_repo / "backend" / "main.py", "print('candidate')\n")
        _write(candidate_repo / "frontend" / "dist" / "index.html", "<!doctype html>\n")

        known_good_bundle, known_good_manifest = _build_bundle(
            known_good_repo,
            artifacts_root,
            "refs/tags/v1.2.0",
            "known-good-sha",
        )
        candidate_bundle, candidate_manifest = _build_bundle(
            candidate_repo,
            artifacts_root,
            "refs/tags/v1.2.1",
            "candidate-sha",
        )

        _write(project_dir / ".env", "GOAT_SERVER_PORT=62606\n")

        result = exercise_release_rollback_drill(
            known_good_bundle=known_good_bundle,
            known_good_manifest=known_good_manifest,
            candidate_bundle=candidate_bundle,
            candidate_manifest=candidate_manifest,
            project_dir=project_dir,
        )

        current_manifest = load_release_manifest(Path(result.current_manifest_path))
        previous_manifest = load_release_manifest(Path(result.previous_manifest_path))

        assert current_manifest["resolved_sha"] == "known-good-sha"
        assert previous_manifest["resolved_sha"] == "candidate-sha"
        assert result.known_good_tree_sha256 == result.rolled_back_tree_sha256
        assert (project_dir / "backend" / "main.py").read_text(encoding="utf-8") == (
            "print('known-good')\n"
        )
        assert (project_dir / ".env").read_text(
            encoding="utf-8"
        ) == "GOAT_SERVER_PORT=62606\n"
