from __future__ import annotations

import re
import unittest
from pathlib import Path


class DocsLanguageTests(unittest.TestCase):
    def test_docs_and_memory_remain_english_only(self) -> None:
        root = Path(__file__).resolve().parents[1]
        targets = [
            root / "README.md",
            root / "AGENTS.md",
            *sorted((root / "docs").glob("*.md")),
            *sorted((root / "docs").glob("*.json")),
            *sorted((root / "docs").glob("*.yaml")),
            *sorted((root / "docs").glob("*.yml")),
            *sorted((root / ".cursor" / "rules").glob("*.mdc")),
        ]

        han_pattern = re.compile(r"[\u4e00-\u9fff]")
        mojibake_pattern = re.compile(r"[鈥鈫搂閴脳鉁鉂馃]")
        replacement_char = "\uFFFD"

        violations: list[str] = []
        for path in targets:
            text = path.read_text(encoding="utf-8")
            if text.startswith("\ufeff"):
                violations.append(f"{path.relative_to(root)}:1: BOM header present")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if han_pattern.search(line) or mojibake_pattern.search(line) or replacement_char in line:
                    violations.append(f"{path.relative_to(root)}:{lineno}: {line}")

        self.assertEqual([], violations, "Docs and memory files must stay English-only and free of mojibake")


if __name__ == "__main__":
    unittest.main()
