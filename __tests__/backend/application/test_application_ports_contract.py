from __future__ import annotations

import ast
from pathlib import Path
import unittest

from __tests__.helpers.repo_root import repo_root
from backend.application import ports


REPO_ROOT = repo_root(Path(__file__))
_TARGET_DIRS = (
    REPO_ROOT / "backend" / "application",
    REPO_ROOT / "backend" / "routers",
)
_FORBIDDEN_IMPORTS = {
    "backend.services.chat_capacity_service",
    "backend.services.exceptions",
}
_FORBIDDEN_TYPES_IMPORTS = {"LLMClient", "Settings"}
_EXPECTED_EXPORTS = {
    "ChatCapacityError",
    "ConversationLogger",
    "FeatureNotAvailable",
    "InferenceBackendUnavailable",
    "KnowledgeDocumentNotFound",
    "KnowledgeValidationError",
    "LLMClient",
    "MediaNotFound",
    "MediaValidationError",
    "SafeguardService",
    "SessionRepository",
    "Settings",
    "TabularContextExtractor",
    "TitleGenerator",
    "VisionNotSupported",
}


def _scan_module_for_forbidden_imports(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if path.name != "ports.py" and node.module in _FORBIDDEN_IMPORTS:
                offenders.append(node.module)
            if path.name != "ports.py" and node.module == "backend.types":
                bad_names = [
                    alias.name
                    for alias in node.names
                    if alias.name in _FORBIDDEN_TYPES_IMPORTS
                ]
                offenders.extend(f"{node.module}:{name}" for name in bad_names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if path.name != "ports.py" and alias.name in _FORBIDDEN_IMPORTS:
                    offenders.append(alias.name)
    return offenders


class ApplicationPortsContractTests(unittest.TestCase):
    def test_ports_exports_stable_surface(self) -> None:
        self.assertTrue(_EXPECTED_EXPORTS.issubset(set(ports.__all__)))

    def test_application_and_router_modules_do_not_import_service_boundaries_directly(
        self,
    ) -> None:
        offenders: list[str] = []
        for directory in _TARGET_DIRS:
            for path in sorted(directory.glob("*.py")):
                if path.name == "__init__.py":
                    continue
                bad = _scan_module_for_forbidden_imports(path)
                offenders.extend(
                    f"{path.relative_to(REPO_ROOT)} -> {item}" for item in bad
                )

        self.assertFalse(
            offenders,
            "application/router modules must import shared contracts from backend.application.ports "
            f"instead of services.exceptions or chat_capacity_service: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
