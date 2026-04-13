from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.desktop.build_desktop_sidecar as subject


def test_find_rustc_prefers_path_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject.shutil, "which", lambda _: "/toolchain/rustc")

    assert subject._find_rustc() == Path("/toolchain/rustc")


def test_find_rustc_falls_back_to_cargo_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fallback = tmp_path / ".cargo" / "bin" / "rustc"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("", encoding="utf-8")

    monkeypatch.setattr(subject.shutil, "which", lambda _: None)
    monkeypatch.setattr(subject.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(subject.sys, "platform", "linux")

    assert subject._find_rustc() == fallback


def test_detect_target_triple_returns_host_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_find_rustc", lambda: Path("/toolchain/rustc"))
    completed = SimpleNamespace(stdout="x86_64-unknown-linux-gnu\n")
    captured: dict[str, object] = {}

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return completed

    monkeypatch.setattr(subject.subprocess, "run", fake_run)

    assert subject._detect_target_triple() == "x86_64-unknown-linux-gnu"
    command = captured["args"][0]  # type: ignore[index]
    assert isinstance(command, list)
    assert Path(command[0]) == Path("/toolchain/rustc")
    assert command[1:] == ["--print", "host-tuple"]
    assert captured["kwargs"] == {
        "check": True,
        "capture_output": True,
        "text": True,
        "cwd": str(subject.REPO_ROOT),
    }


def test_detect_target_triple_fails_without_rustc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_find_rustc", lambda: None)

    with pytest.raises(SystemExit, match="Could not find rustc"):
        subject._detect_target_triple()


def test_add_data_arg_uses_platform_separator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject.sys, "platform", "win32")
    assert subject._add_data_arg(Path("a"), "b") == "a;b"

    monkeypatch.setattr(subject.sys, "platform", "linux")
    assert subject._add_data_arg(Path("a"), "b") == "a:b"


def test_main_builds_and_installs_sidecar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = tmp_path / "repo"
    binaries_dir = repo_root / "frontend" / "src-tauri" / "binaries"
    build_root = repo_root / "frontend" / "src-tauri" / ".desktop-sidecar-build"
    entrypoint = repo_root / "goat_ai" / "runtime" / "desktop_sidecar.py"
    migrations_dir = repo_root / "backend" / "migrations"
    entrypoint.parent.mkdir(parents=True)
    migrations_dir.mkdir(parents=True)
    entrypoint.write_text("print('desktop')\n", encoding="utf-8")

    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            argparse.Namespace(target_triple="x86_64-pc-windows-msvc", clean=True)
        ),
    )
    monkeypatch.setattr(subject, "REPO_ROOT", repo_root)
    monkeypatch.setattr(subject, "BINARIES_DIR", binaries_dir)
    monkeypatch.setattr(subject, "BUILD_ROOT", build_root)
    monkeypatch.setattr(subject, "ENTRYPOINT", entrypoint)
    monkeypatch.setattr(subject.sys, "platform", "win32")
    monkeypatch.setattr(subject.sys, "executable", "C:/Python314/python.exe")

    removed_paths: list[Path] = []
    monkeypatch.setattr(
        subject.shutil, "rmtree", lambda path: removed_paths.append(Path(path))
    )

    def fake_run(command: list[str], *, check: bool, cwd: str) -> None:
        assert check is True
        assert cwd == str(repo_root)
        assert "--onefile" in command
        assert "--add-data" in command
        add_data_index = command.index("--add-data")
        assert command[add_data_index + 1] == f"{migrations_dir};backend/migrations"
        hidden_import_index = command.index("--hidden-import")
        assert command[hidden_import_index + 1] == "backend.main"
        assert command[-1] == str(entrypoint)
        dist_dir = build_root / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        (dist_dir / "goat-backend-build.exe").write_text("binary", encoding="utf-8")

    monkeypatch.setattr(subject.subprocess, "run", fake_run)

    build_root.mkdir(parents=True)

    subject.main()

    final_binary = binaries_dir / "goat-backend-x86_64-pc-windows-msvc.exe"
    assert removed_paths == [build_root]
    assert final_binary.read_text(encoding="utf-8") == "binary"
    assert capsys.readouterr().out.strip() == str(final_binary)


def test_main_reports_pyinstaller_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "repo"
    entrypoint = repo_root / "goat_ai" / "runtime" / "desktop_sidecar.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("print('desktop')\n", encoding="utf-8")

    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            argparse.Namespace(target_triple="linux", clean=False)
        ),
    )
    monkeypatch.setattr(subject, "REPO_ROOT", repo_root)
    monkeypatch.setattr(
        subject, "BINARIES_DIR", repo_root / "frontend" / "src-tauri" / "binaries"
    )
    monkeypatch.setattr(
        subject,
        "BUILD_ROOT",
        repo_root / "frontend" / "src-tauri" / ".desktop-sidecar-build",
    )
    monkeypatch.setattr(subject, "ENTRYPOINT", entrypoint)
    monkeypatch.setattr(subject.subprocess, "run", _raise_called_process_error)

    with pytest.raises(SystemExit, match="PyInstaller build failed"):
        subject.main()


def _parser_with_namespace(namespace: argparse.Namespace) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser


def _raise_called_process_error(*args: object, **kwargs: object) -> None:
    raise subject.subprocess.CalledProcessError(returncode=1, cmd="pyinstaller")
