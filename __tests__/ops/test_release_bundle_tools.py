from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from tools.build_release_bundle import build_release_bundle
from tools.install_release_bundle import install_release_bundle


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_release_bundle_packages_dist_and_excludes_runtime_state(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "deploy.sh", "#!/usr/bin/env bash\n")
    _write(repo_root / "backend" / "main.py", "print('ok')\n")
    _write(repo_root / "frontend" / "dist" / "index.html", "<!doctype html>\n")
    _write(repo_root / "frontend" / "node_modules" / "left-pad.js", "ignored\n")
    _write(repo_root / "data" / "runtime.txt", "ignored\n")
    _write(repo_root / "logs" / "fastapi.log", "ignored\n")
    _write(repo_root / "chat_logs.db", "ignored\n")
    _write(repo_root / ".git" / "config", "[core]\n")

    bundle_path = tmp_path / "artifacts" / "release-bundle.tar.gz"
    manifest_path = tmp_path / "artifacts" / "release-manifest.json"

    manifest = build_release_bundle(
        repo_root=repo_root,
        output_bundle=bundle_path,
        output_manifest=manifest_path,
        release_ref="main",
        resolved_sha="abc123",
        actor="tester",
    )

    with tarfile.open(bundle_path, "r:gz") as archive:
        names = set(archive.getnames())

    assert "deploy.sh" in names
    assert "backend/main.py" in names
    assert "frontend/dist/index.html" in names
    assert "frontend/node_modules/left-pad.js" not in names
    assert "data/runtime.txt" not in names
    assert "logs/fastapi.log" not in names
    assert "chat_logs.db" not in names
    assert ".git/config" not in names

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["release_ref"] == "main"
    assert payload["resolved_sha"] == "abc123"
    assert payload["bundle_sha256"] == manifest.bundle_sha256
    assert payload["frontend_dist_included"] is True
    assert payload["file_count"] == 3


def test_install_release_bundle_replaces_source_tree_but_preserves_runtime_paths(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "deploy.sh", "#!/usr/bin/env bash\necho deploy\n")
    _write(repo_root / "backend" / "main.py", "print('new bundle')\n")
    _write(repo_root / "frontend" / "dist" / "index.html", "<!doctype html>\n")

    bundle_path = tmp_path / "artifacts" / "release-bundle.tar.gz"
    manifest_path = tmp_path / "artifacts" / "release-manifest.json"
    build_release_bundle(
        repo_root=repo_root,
        output_bundle=bundle_path,
        output_manifest=manifest_path,
        release_ref="refs/tags/v1.2.0",
        resolved_sha="feedface",
        actor="tester",
    )

    project_dir = tmp_path / "project"
    _write(project_dir / ".env", "GOAT_SERVER_PORT=62606\n")
    _write(project_dir / "logs" / "fastapi.log", "keep\n")
    _write(project_dir / "data" / "upload.txt", "keep\n")
    _write(project_dir / ".git" / "config", "[core]\n")
    _write(project_dir / "obsolete.txt", "remove me\n")

    install_release_bundle(
        bundle_path=bundle_path,
        manifest_path=manifest_path,
        project_dir=project_dir,
        expected_sha="feedface",
    )

    assert (project_dir / "deploy.sh").is_file()
    assert (project_dir / "backend" / "main.py").read_text(
        encoding="utf-8"
    ) == "print('new bundle')\n"
    assert (project_dir / "frontend" / "dist" / "index.html").is_file()
    assert (project_dir / ".env").read_text(
        encoding="utf-8"
    ) == "GOAT_SERVER_PORT=62606\n"
    assert (project_dir / "logs" / "fastapi.log").read_text(
        encoding="utf-8"
    ) == "keep\n"
    assert (project_dir / "data" / "upload.txt").read_text(encoding="utf-8") == "keep\n"
    assert (project_dir / ".git" / "config").is_file()
    assert not (project_dir / "obsolete.txt").exists()


def test_install_release_bundle_rejects_sha_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "deploy.sh", "#!/usr/bin/env bash\n")
    _write(repo_root / "frontend" / "dist" / "index.html", "<!doctype html>\n")

    bundle_path = tmp_path / "artifacts" / "release-bundle.tar.gz"
    manifest_path = tmp_path / "artifacts" / "release-manifest.json"
    build_release_bundle(
        repo_root=repo_root,
        output_bundle=bundle_path,
        output_manifest=manifest_path,
        release_ref="main",
        resolved_sha="cafebabe",
        actor="tester",
    )

    with pytest.raises(ValueError, match="did not match EXPECTED_GIT_SHA"):
        install_release_bundle(
            bundle_path=bundle_path,
            manifest_path=manifest_path,
            project_dir=tmp_path / "project",
            expected_sha="deadbeef",
        )
