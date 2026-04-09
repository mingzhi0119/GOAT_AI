"""Fail if HTTP routers gain direct imports of shared/runtime or heavy I/O stacks.

Layering between packages is enforced by ``lint-imports`` (see ``pyproject.toml``).
This file adds a cheap, explicit guard on *direct* imports in ``backend/routers/*.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ROUTER_DIR = Path(__file__).resolve().parent.parent / "backend" / "routers"
_FORBIDDEN_TOPLEVEL = frozenset({"goat_ai", "httpx", "requests", "pandas", "openpyxl"})


def _collect_forbidden_modules(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if top in _FORBIDDEN_TOPLEVEL:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".", 1)[0]
            if top in _FORBIDDEN_TOPLEVEL:
                found.append(node.module)
    return found


@pytest.mark.parametrize(
    "path",
    sorted(_ROUTER_DIR.glob("*.py")),
    ids=lambda p: p.name,
)
def test_router_files_avoid_forbidden_direct_imports(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    bad = _collect_forbidden_modules(tree)
    assert not bad, (
        f"{path.relative_to(path.parents[2])}: forbidden direct imports {bad}"
    )
