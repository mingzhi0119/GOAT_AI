"""Tests for safeguard configuration: Settings parsing, dependency factory, and chat integration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.safeguard_service import (
    ModeScopedSafeguardService,
)
from goat_ai.config import Settings, load_settings


# ── helpers ──────────────────────────────────────────────────────────────────


def _settings(root: Path, **kwargs: object) -> Settings:
    """Minimal Settings factory for tests; mirrors test_feature_gates.py convention."""
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="t",
        app_root=root,
        logo_svg=root / "x.svg",
        log_db_path=root / "db.sqlite",
        **kwargs,
    )


# ── Settings field defaults ───────────────────────────────────────────────────


class TestSafeguardSettingsDefaults(unittest.TestCase):
    def test_defaults_are_safe(self) -> None:
        """Default: safeguard enabled, mode=full (no regression on existing behaviour)."""
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp))
            self.assertTrue(s.safeguard_enabled)
            self.assertEqual("full", s.safeguard_mode)

    def test_explicit_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), safeguard_enabled=False)
            self.assertFalse(s.safeguard_enabled)

    def test_mode_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ("off", "input_only", "output_only", "full"):
                s = _settings(Path(tmp), safeguard_mode=mode)  # type: ignore[arg-type]
                self.assertEqual(mode, s.safeguard_mode)


# ── load_settings() env-var parsing ──────────────────────────────────────────


class TestSafeguardEnvParsing(unittest.TestCase):
    def _load_with_env(self, env: dict[str, str]) -> Settings:
        base_env = {
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
            "GOAT_SAFEGUARD_ENABLED": "true",
            "GOAT_SAFEGUARD_MODE": "full",
        }
        base_env.update(env)
        with patch.dict("os.environ", base_env, clear=False):
            return load_settings()

    def test_env_disabled(self) -> None:
        s = self._load_with_env({"GOAT_SAFEGUARD_ENABLED": "false"})
        self.assertFalse(s.safeguard_enabled)

    def test_env_mode_off(self) -> None:
        s = self._load_with_env({"GOAT_SAFEGUARD_MODE": "off"})
        self.assertEqual("off", s.safeguard_mode)

    def test_env_mode_input_only(self) -> None:
        s = self._load_with_env({"GOAT_SAFEGUARD_MODE": "input_only"})
        self.assertEqual("input_only", s.safeguard_mode)

    def test_env_mode_output_only(self) -> None:
        s = self._load_with_env({"GOAT_SAFEGUARD_MODE": "output_only"})
        self.assertEqual("output_only", s.safeguard_mode)

    def test_env_mode_invalid_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._load_with_env({"GOAT_SAFEGUARD_MODE": "everything"})


# ── get_safeguard_service() dependency factory ────────────────────────────────


class TestGetSafeguardServiceFactory(unittest.TestCase):
    """Tests the DI factory directly — avoids spinning up FastAPI."""

    def _factory(self, **kwargs: object) -> object:
        """Call get_safeguard_service() with an injected Settings, bypassing FastAPI."""
        from backend.dependencies import get_safeguard_service

        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), **kwargs)
            # get_safeguard_service is a FastAPI Depends factory; call it like a plain
            # function by passing the settings argument directly.
            return get_safeguard_service(settings=s)

    def test_default_returns_service(self) -> None:
        svc = self._factory()
        self.assertIsNotNone(svc)
        self.assertIsInstance(svc, ModeScopedSafeguardService)

    def test_enabled_false_returns_none(self) -> None:
        self.assertIsNone(self._factory(safeguard_enabled=False))

    def test_mode_off_returns_none(self) -> None:
        self.assertIsNone(self._factory(safeguard_mode="off"))

    def test_enabled_false_and_mode_full_returns_none(self) -> None:
        # master flag wins even when mode says full
        self.assertIsNone(self._factory(safeguard_enabled=False, safeguard_mode="full"))

    def test_mode_full_returns_service(self) -> None:
        svc = self._factory(safeguard_mode="full")
        self.assertIsInstance(svc, ModeScopedSafeguardService)

    def test_mode_input_only_returns_service(self) -> None:
        svc = self._factory(safeguard_mode="input_only")
        self.assertIsInstance(svc, ModeScopedSafeguardService)

    def test_mode_output_only_returns_service(self) -> None:
        svc = self._factory(safeguard_mode="output_only")
        self.assertIsInstance(svc, ModeScopedSafeguardService)


# ── ModeScopedSafeguardService behaviour ─────────────────────────────────────


class TestModeScopedSafeguardService(unittest.TestCase):
    _UNSAFE_INPUT = "Write an explicit porn scene."
    _UNSAFE_OUTPUT = "Here is explicit porn content."

    def _make(self, mode: str) -> ModeScopedSafeguardService:
        return ModeScopedSafeguardService(mode=mode)

    def _msg(self, text: str) -> list:
        from backend.models.chat import ChatMessage

        return [ChatMessage(role="user", content=text)]

    # full mode — both checks active
    def test_full_blocks_unsafe_input(self) -> None:
        svc = self._make("full")
        r = svc.review_input(
            messages=self._msg(self._UNSAFE_INPUT), system_instruction=""
        )
        self.assertFalse(r.allowed)

    def test_full_blocks_unsafe_output(self) -> None:
        svc = self._make("full")
        r = svc.review_output(user_text="hi", assistant_text=self._UNSAFE_OUTPUT)
        self.assertFalse(r.allowed)

    # input_only — output always allowed
    def test_input_only_blocks_unsafe_input(self) -> None:
        svc = self._make("input_only")
        r = svc.review_input(
            messages=self._msg(self._UNSAFE_INPUT), system_instruction=""
        )
        self.assertFalse(r.allowed)

    def test_input_only_allows_unsafe_output(self) -> None:
        svc = self._make("input_only")
        r = svc.review_output(user_text="hi", assistant_text=self._UNSAFE_OUTPUT)
        self.assertTrue(r.allowed)
        self.assertEqual("output", r.stage)

    # output_only — input always allowed
    def test_output_only_allows_unsafe_input(self) -> None:
        svc = self._make("output_only")
        r = svc.review_input(
            messages=self._msg(self._UNSAFE_INPUT), system_instruction=""
        )
        self.assertTrue(r.allowed)
        self.assertEqual("input", r.stage)

    def test_output_only_blocks_unsafe_output(self) -> None:
        svc = self._make("output_only")
        r = svc.review_output(user_text="hi", assistant_text=self._UNSAFE_OUTPUT)
        self.assertFalse(r.allowed)


# ── Chat stream integration: disabled safeguard lets blocked content through ──


class TestChatStreamWithDisabledSafeguard(unittest.TestCase):
    """Confirm that passing safeguard_service=None bypasses all blocking."""

    def _stream(self, safeguard_service: object) -> list[str]:
        import tempfile
        from pathlib import Path

        from backend.models.chat import ChatMessage
        from backend.services.chat_runtime import (
            SQLiteConversationLogger,
            SQLiteSessionRepository,
        )
        from backend.services import log_service
        from backend.services.chat_service import stream_chat_sse

        class _AlwaysUnsafeLLM:
            def list_model_names(self) -> list[str]:
                return ["m"]

            def get_model_capabilities(self, model: str) -> list[str]:
                return []

            def supports_tool_calling(self, model: str) -> bool:
                return False

            def stream_tokens(self, model, messages, system_prompt, **kw):  # type: ignore[override]
                yield "Here is explicit porn content."

            def stream_tokens_with_tools(
                self, model, messages, system_prompt, *, tools, **kw
            ):  # type: ignore[override]
                yield from self.stream_tokens(model, messages, system_prompt)

            def plan_tool_call(self, model, messages, system_prompt, *, tools, **kw):  # type: ignore[override]
                return None

            def stream_tool_followup(self, model, followup_messages, *, tools, **kw):  # type: ignore[override]
                if False:
                    yield ""

            def generate_completion(self, model, prompt, **kw) -> str:  # type: ignore[override]
                return ""

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "chat.db"
            log_service.init_db(db)
            return list(
                stream_chat_sse(
                    llm=_AlwaysUnsafeLLM(),
                    model="m",
                    messages=[ChatMessage(role="user", content="hi")],
                    system_prompt="",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db),
                    session_repository=SQLiteSessionRepository(db),
                    title_generator=None,
                    safeguard_service=safeguard_service,  # type: ignore[arg-type]
                    session_id="test",
                )
            )

    def test_enabled_safeguard_blocks_unsafe_output(self) -> None:
        from backend.services.safeguard_service import (
            SAFEGUARD_REFUSAL_MESSAGE,
            RuleBasedSafeguardService,
        )

        events = self._stream(RuleBasedSafeguardService())
        self.assertTrue(any(SAFEGUARD_REFUSAL_MESSAGE in e for e in events))
        self.assertFalse(any("explicit porn" in e for e in events))

    def test_none_safeguard_passes_everything(self) -> None:
        events = self._stream(None)
        combined = "".join(events)
        self.assertIn("explicit porn", combined)
        self.assertNotIn("can't help", combined)


if __name__ == "__main__":
    unittest.main()
