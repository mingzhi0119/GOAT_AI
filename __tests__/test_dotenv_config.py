from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from goat_ai import config


class DotenvConfigTests(unittest.TestCase):
    def test_load_dotenv_file_sets_missing_values_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv_path = Path(tmp) / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "OLLAMA_BASE_URL=http://127.0.0.1:11435",
                        "QUOTED_VALUE='hello world'",
                        'DOUBLE_QUOTED="hello again"',
                    ]
                ),
                encoding="utf-8",
            )

            original = {
                "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL"),
                "QUOTED_VALUE": os.environ.get("QUOTED_VALUE"),
                "DOUBLE_QUOTED": os.environ.get("DOUBLE_QUOTED"),
            }
            try:
                os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9999"
                os.environ.pop("QUOTED_VALUE", None)
                os.environ.pop("DOUBLE_QUOTED", None)

                config._load_dotenv_file(dotenv_path)

                self.assertEqual(os.environ["OLLAMA_BASE_URL"], "http://127.0.0.1:9999")
                self.assertEqual(os.environ["QUOTED_VALUE"], "hello world")
                self.assertEqual(os.environ["DOUBLE_QUOTED"], "hello again")
            finally:
                for key, value in original.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
