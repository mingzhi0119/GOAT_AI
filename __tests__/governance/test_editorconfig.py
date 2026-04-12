from __future__ import annotations

import unittest
from pathlib import Path

from __tests__.helpers.repo_root import repo_root


class EditorConfigTests(unittest.TestCase):
    def test_root_editorconfig_enforces_utf8_without_bom(self) -> None:
        root = repo_root(Path(__file__))
        editorconfig = root / ".editorconfig"

        self.assertTrue(
            editorconfig.exists(), ".editorconfig must exist at the repo root"
        )

        raw = editorconfig.read_bytes()
        self.assertFalse(
            raw.startswith(b"\xef\xbb\xbf"), ".editorconfig must not use a UTF-8 BOM"
        )

        text = editorconfig.read_text(encoding="utf-8")
        self.assertIn("root = true", text)
        self.assertIn("charset = utf-8", text)
        self.assertIn("end_of_line = lf", text)
        self.assertIn("insert_final_newline = true", text)
        self.assertIn("trim_trailing_whitespace = true", text)
        self.assertNotIn("utf-8-bom", text)


if __name__ == "__main__":
    unittest.main()
