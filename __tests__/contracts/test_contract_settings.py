from __future__ import annotations

import os
import unittest
from unittest.mock import patch, sentinel

from tools.contracts import _contract_settings


class ContractSettingsTests(unittest.TestCase):
    def test_load_contract_settings_forces_local_mode_and_restores_env(self) -> None:
        original_env = {"GOAT_DEPLOY_MODE": "2", "GOAT_RUNTIME_ROOT": "orig-root"}
        captured: dict[str, str | None] = {}

        def fake_load_settings() -> object:
            captured["deploy_mode"] = os.environ.get("GOAT_DEPLOY_MODE")
            captured["runtime_root"] = os.environ.get("GOAT_RUNTIME_ROOT")
            return sentinel.contract_settings

        with patch.dict(os.environ, original_env, clear=True):
            with patch.object(
                _contract_settings, "load_settings", side_effect=fake_load_settings
            ):
                result = _contract_settings.load_contract_settings()

            self.assertEqual("2", os.environ["GOAT_DEPLOY_MODE"])
            self.assertEqual("orig-root", os.environ["GOAT_RUNTIME_ROOT"])

        self.assertIs(result, sentinel.contract_settings)
        self.assertEqual("0", captured["deploy_mode"])
        self.assertIsNotNone(captured["runtime_root"])

    def test_load_contract_settings_works_without_existing_env(self) -> None:
        captured: dict[str, str | None] = {}

        def fake_load_settings() -> object:
            captured["deploy_mode"] = os.environ.get("GOAT_DEPLOY_MODE")
            captured["runtime_root"] = os.environ.get("GOAT_RUNTIME_ROOT")
            return sentinel.contract_settings

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                _contract_settings, "load_settings", side_effect=fake_load_settings
            ):
                result = _contract_settings.load_contract_settings()

            self.assertNotIn("GOAT_DEPLOY_MODE", os.environ)
            self.assertNotIn("GOAT_RUNTIME_ROOT", os.environ)

        self.assertIs(result, sentinel.contract_settings)
        self.assertEqual("0", captured["deploy_mode"])
        self.assertIsNotNone(captured["runtime_root"])


if __name__ == "__main__":
    unittest.main()
