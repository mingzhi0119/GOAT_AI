from __future__ import annotations

import json
from pathlib import Path

import pytest

from __tests__.helpers.repo_root import repo_root
import tools.desktop.write_desktop_release_provenance as subject


REPO_ROOT = repo_root(Path(__file__))


def test_build_provenance_payload_records_expected_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_root = tmp_path / "bundle"
    msi_dir = bundle_root / "msi"
    nsis_dir = bundle_root / "nsis"
    msi_dir.mkdir(parents=True)
    nsis_dir.mkdir(parents=True)
    (msi_dir / "GOAT AI_1.2.0_x64_en-US.msi").write_bytes(b"msi")
    (nsis_dir / "GOAT AI_1.2.0_x64-setup.exe").write_bytes(b"nsis")

    monkeypatch.setattr(subject, "authenticode_status", lambda path: None)

    payload = subject.build_provenance_payload(
        bundle_root=bundle_root,
        patterns=["msi/*.msi", "nsis/*-setup.exe"],
        release_ref="refs/tags/v1.2.0",
        resolved_sha="abc123",
        platform_label="windows-x64",
        distribution_channel="internal_test",
        require_signed=False,
        cwd=tmp_path,
    )

    assert payload["distribution_channel"] == "internal_test"
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    assert len(artifacts) == 2
    assert {artifact["file_name"] for artifact in artifacts} == {
        "GOAT AI_1.2.0_x64_en-US.msi",
        "GOAT AI_1.2.0_x64-setup.exe",
    }


def test_build_provenance_payload_requires_signed_artifacts_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_root = tmp_path / "bundle"
    msi_dir = bundle_root / "msi"
    nsis_dir = bundle_root / "nsis"
    msi_dir.mkdir(parents=True)
    nsis_dir.mkdir(parents=True)
    (msi_dir / "GOAT AI_1.2.0_x64_en-US.msi").write_bytes(b"msi")
    (nsis_dir / "GOAT AI_1.2.0_x64-setup.exe").write_bytes(b"nsis")
    monkeypatch.setattr(subject, "authenticode_status", lambda path: "NotSigned")

    with pytest.raises(SystemExit, match="Expected signed desktop artifact"):
        subject.build_provenance_payload(
            bundle_root=bundle_root,
            patterns=["msi/*.msi", "nsis/*-setup.exe"],
            release_ref="refs/tags/v1.2.0",
            resolved_sha="abc123",
            platform_label="windows-x64",
            distribution_channel="public",
            require_signed=True,
            cwd=tmp_path,
        )


def test_ci_and_provenance_workflows_cover_packaged_desktop_release_path() -> None:
    ci_workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    desktop_provenance = (
        REPO_ROOT / ".github" / "workflows" / "desktop-provenance.yml"
    ).read_text(encoding="utf-8")
    release_doc = (
        REPO_ROOT / "docs" / "operations" / "RELEASE_GOVERNANCE.md"
    ).read_text(encoding="utf-8")
    security_doc = (REPO_ROOT / "docs" / "governance" / "SECURITY.md").read_text(
        encoding="utf-8"
    )
    roadmap = (REPO_ROOT / "docs" / "governance" / "ROADMAP.md").read_text(
        encoding="utf-8"
    )

    assert "desktop-package-windows" in ci_workflow
    assert "runs-on: windows-latest" in ci_workflow
    assert "npm run desktop:build" in ci_workflow
    assert "python -m tools.desktop.write_desktop_release_provenance" in ci_workflow

    assert (
        "python -m tools.desktop.write_linux_sidecar_provenance" in desktop_provenance
    )
    assert "desktop-sidecar.spdx.json" in desktop_provenance
    assert "x86_64-unknown-linux-gnu" in desktop_provenance
    assert "GOAT_DESKTOP_SIGNING_CERT_BASE64" in desktop_provenance
    assert "sign_windows_desktop_artifacts.ps1" in desktop_provenance
    assert "desktop-windows-provenance.json" in desktop_provenance
    assert desktop_provenance.count("actions/attest@v4") >= 4

    assert "signed Windows desktop release path" in release_doc
    assert "Linux desktop sidecar provenance record" in release_doc
    assert "desktop-provenance.yml" in release_doc
    assert "Publicly distributed Windows desktop installers" in security_doc
    assert "No open P1 audit items remain" in roadmap


def test_main_writes_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_root = tmp_path / "bundle"
    msi_dir = bundle_root / "msi"
    nsis_dir = bundle_root / "nsis"
    msi_dir.mkdir(parents=True)
    nsis_dir.mkdir(parents=True)
    (msi_dir / "GOAT AI_1.2.0_x64_en-US.msi").write_bytes(b"msi")
    (nsis_dir / "GOAT AI_1.2.0_x64-setup.exe").write_bytes(b"nsis")
    output_path = tmp_path / "desktop-provenance.json"
    monkeypatch.setattr(subject, "authenticode_status", lambda path: None)
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            bundle_root=str(bundle_root),
            pattern=["msi/*.msi", "nsis/*-setup.exe"],
            output=str(output_path),
            release_ref="refs/tags/v1.2.0",
            resolved_sha="abc123",
            platform="windows-x64",
            distribution_channel="internal_test",
            require_signed=False,
        ),
    )

    subject.main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["platform"] == "windows-x64"
    assert len(payload["artifacts"]) == 2


def _parser_with_namespace(**kwargs: object):
    parser = subject.argparse.ArgumentParser()
    namespace = type("Args", (), kwargs)()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser
