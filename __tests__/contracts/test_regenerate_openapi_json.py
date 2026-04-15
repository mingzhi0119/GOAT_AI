from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import mock_open, patch

from tools.contracts import regenerate_openapi_json


class RegenerateOpenapiJsonTests(unittest.TestCase):
    def test_main_writes_lf_newlines(self) -> None:
        app = SimpleNamespace(openapi=lambda: {"openapi": "3.1.0", "paths": {}})
        handle = mock_open()

        with (
            patch.object(
                regenerate_openapi_json,
                "load_contract_settings",
                return_value=SimpleNamespace(),
            ),
            patch.object(
                regenerate_openapi_json,
                "create_contract_app",
                return_value=app,
            ),
            patch.object(regenerate_openapi_json.Path, "open", handle),
        ):
            regenerate_openapi_json.main()

        self.assertEqual(1, handle.call_count)
        _, kwargs = handle.call_args
        self.assertEqual("utf-8", kwargs["encoding"])
        self.assertEqual("\n", kwargs["newline"])


if __name__ == "__main__":
    unittest.main()
