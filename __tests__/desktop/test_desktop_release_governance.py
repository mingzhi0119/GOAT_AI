from __future__ import annotations

import json
from pathlib import Path

import pytest

from __tests__.helpers.repo_root import repo_root
import tools.desktop.write_desktop_release_provenance as subject


REPO_ROOT = repo_root(Path(__file__))


def _workflow_job_block(workflow_text: str, job_name: str) -> str:
    lines = workflow_text.splitlines()
    start_index = lines.index(f"  {job_name}:")
    block_lines: list[str] = []
    for line in lines[start_index + 1 :]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        block_lines.append(line)
    return "\n".join(block_lines)


def _workflow_filter_block(workflow_text: str, filter_name: str) -> str:
    lines = workflow_text.splitlines()
    start_index = lines.index(f"            {filter_name}:")
    block_lines: list[str] = []
    for line in lines[start_index + 1 :]:
        if line.startswith("            ") and not line.startswith("              "):
            break
        block_lines.append(line)
    return "\n".join(block_lines)


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
    fault_injection = (
        REPO_ROOT / ".github" / "workflows" / "fault-injection.yml"
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
    operations_doc = (REPO_ROOT / "docs" / "operations" / "OPERATIONS.md").read_text(
        encoding="utf-8"
    )
    incident_triage = (
        REPO_ROOT / "docs" / "operations" / "INCIDENT_TRIAGE.md"
    ).read_text(encoding="utf-8")
    changes_filter = _workflow_filter_block(ci_workflow, "desktop")
    desktop_windows_job = _workflow_job_block(ci_workflow, "desktop-package-windows")
    desktop_supply_chain_job = _workflow_job_block(ci_workflow, "desktop-supply-chain")

    assert "desktop-package-windows" in ci_workflow
    assert "runs-on: windows-latest" in ci_workflow
    assert "npm run desktop:build" in ci_workflow
    assert "'frontend/src/**'" in changes_filter
    assert "'frontend/public/**'" in changes_filter
    assert "'frontend/index.html'" in changes_filter
    assert "'frontend/vite.config.ts'" in changes_filter
    assert "'frontend/tsconfig*.json'" in changes_filter
    assert "'frontend/postcss.config.cjs'" in changes_filter
    assert "'frontend/tailwind.config.cjs'" in changes_filter
    assert "'__tests__/desktop/**'" in changes_filter
    assert "'__tests__/ops/test_ops_asset_contracts.py'" in changes_filter
    assert "needs.changes.outputs.desktop_changed == 'true'" in ci_workflow
    assert "python -m tools.desktop.packaged_shell_fault_smoke" in desktop_windows_job
    assert "desktop-windows-fault-smoke" in desktop_windows_job
    assert "if: ${{ always() }}" in desktop_windows_job
    assert ci_workflow.count("python -m tools.desktop.packaged_shell_fault_smoke") == 1
    assert (
        "python -m tools.desktop.packaged_shell_fault_smoke"
        not in desktop_supply_chain_job
    )
    assert "--scenario missing_sidecar" in desktop_windows_job
    assert "--scenario exit_before_ready" in desktop_windows_job
    assert "--scenario hang_before_ready" in desktop_windows_job
    assert "--startup-timeout-sec 20" in desktop_windows_job
    assert "--health-timeout-sec 2" in desktop_windows_job
    assert "--restart-limit 1" in desktop_windows_job
    assert "--backoff-ms 100" in desktop_windows_job
    assert "--hang-sec 5" in desktop_windows_job
    assert "Build Linux desktop sidecar" in desktop_supply_chain_job
    assert "Rust dependency audit" in desktop_supply_chain_job
    assert "python -m tools.desktop.write_desktop_release_provenance" in ci_workflow

    assert (
        "python -m tools.desktop.write_linux_sidecar_provenance" in desktop_provenance
    )
    assert "desktop-sidecar.spdx.json" in desktop_provenance
    assert "x86_64-unknown-linux-gnu" in desktop_provenance
    assert "GOAT_DESKTOP_SIGNING_CERT_BASE64" in desktop_provenance
    assert "sign_windows_desktop_artifacts.ps1" in desktop_provenance
    assert "desktop-windows-provenance.json" in desktop_provenance
    assert (
        desktop_provenance.count(
            "python -m tools.desktop.installed_windows_desktop_fault_smoke"
        )
        == 2
    )
    assert "desktop-windows-installed-smoke" in desktop_provenance
    assert desktop_provenance.count("actions/attest@v4") >= 4
    assert "windows-installed-desktop-drill" in fault_injection
    assert (
        fault_injection.count(
            "python -m tools.desktop.installed_windows_desktop_fault_smoke"
        )
        == 2
    )
    assert "desktop-installed-drill" in fault_injection
    assert "python -m tools.desktop.packaged_shell_fault_smoke" not in fault_injection

    assert "signed Windows desktop release path" in release_doc
    assert "Linux desktop sidecar provenance record" in release_doc
    assert "packaged-shell fault smoke" in release_doc
    assert "installed Windows startup evidence" in release_doc
    assert "desktop-windows-installed-smoke" not in release_doc
    assert "fault-injection.yml" in release_doc
    assert "desktop-provenance.yml" in release_doc
    assert "Publicly distributed Windows desktop installers" in security_doc
    assert "No open P1 audit items remain" in roadmap
    assert "backend-fast" in roadmap
    assert "merge-blocking packaged-shell fault smoke" in roadmap
    assert "desktop-package-windows" in roadmap
    assert "merge-blocking packaged-shell fault smoke" in roadmap
    assert "packaged-build truth set" in operations_doc
    assert "non-desktop-only backend or documentation changes" in operations_doc
    assert "frontend build inputs" in incident_triage
    assert "non-desktop-only backend or documentation changes" in incident_triage


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
