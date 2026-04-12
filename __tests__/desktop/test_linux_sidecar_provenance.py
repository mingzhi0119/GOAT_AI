from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.desktop.write_linux_sidecar_provenance as subject


def test_build_provenance_payload_records_artifact_and_optional_sbom(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "goat-backend-x86_64-unknown-linux-gnu"
    sbom = tmp_path / "desktop-sidecar.spdx.json"
    artifact.write_bytes(b"linux-binary")
    sbom.write_text('{"sbom":"ok"}\n', encoding="utf-8")

    payload = subject.build_provenance_payload(
        artifact=artifact,
        release_ref="refs/tags/v1.2.0",
        resolved_sha="abc123",
        platform_label="linux-x64",
        target_triple="x86_64-unknown-linux-gnu",
        cwd=tmp_path,
        sbom=sbom,
    )

    assert payload["platform"] == "linux-x64"
    assert payload["target_triple"] == "x86_64-unknown-linux-gnu"
    assert payload["artifact"]["file_name"] == artifact.name
    assert payload["sbom"]["file_name"] == sbom.name


def test_build_provenance_payload_requires_existing_artifact(tmp_path: Path) -> None:
    missing = tmp_path / "missing-sidecar"

    with pytest.raises(SystemExit, match="Expected Linux desktop artifact"):
        subject.build_provenance_payload(
            artifact=missing,
            release_ref="refs/tags/v1.2.0",
            resolved_sha="abc123",
            platform_label="linux-x64",
            target_triple="x86_64-unknown-linux-gnu",
            cwd=tmp_path,
        )


def test_main_writes_json_output(tmp_path: Path, monkeypatch) -> None:
    artifact = tmp_path / "goat-backend-x86_64-unknown-linux-gnu"
    artifact.write_bytes(b"linux-binary")
    output_path = tmp_path / "desktop-provenance.json"
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            artifact=str(artifact),
            output=str(output_path),
            release_ref="refs/tags/v1.2.0",
            resolved_sha="abc123",
            platform="linux-x64",
            target_triple="x86_64-unknown-linux-gnu",
            sbom="",
        ),
    )

    subject.main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact"]["file_name"] == artifact.name
    assert payload["target_triple"] == "x86_64-unknown-linux-gnu"


def _parser_with_namespace(**kwargs: object):
    parser = subject.argparse.ArgumentParser()
    namespace = type("Args", (), kwargs)()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser
