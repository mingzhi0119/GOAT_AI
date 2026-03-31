"""Theme bar HTML is injected via st.html in streamlit_app (not raw markdown)."""

from __future__ import annotations

import inspect
import unittest

import goat_ai.streamlit_app as streamlit_app
from goat_ai.theme_controls import FLOATING_THEME_HTML


class ThemeControlsTests(unittest.TestCase):
    def test_floating_theme_html_has_expected_structure(self) -> None:
        """Sanity check for the fixed-position theme bar markup."""
        self.assertIn("goat-theme-bar", FLOATING_THEME_HTML)
        self.assertIn("stActiveTheme", FLOATING_THEME_HTML)
        self.assertIn("Light", FLOATING_THEME_HTML)
        self.assertIn("Dark", FLOATING_THEME_HTML)

    def test_inject_styles_uses_st_html_for_theme_bar(self) -> None:
        """Regression: markdown HTML path mangles onclick and leaks text at page top."""
        src = inspect.getsource(streamlit_app._inject_styles)
        self.assertIn("st.html(FLOATING_THEME_HTML", src)
        self.assertIn("unsafe_allow_javascript=True", src)


if __name__ == "__main__":
    unittest.main()
