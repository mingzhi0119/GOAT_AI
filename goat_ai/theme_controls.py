"""In-app theme switcher using Streamlit's browser theme cache (same as Settings → Theme)."""

from __future__ import annotations

import streamlit.components.v1 as components

# Matches frontend/lib/src/util/storageUtils.ts + theme/utils.ts (CachedTheme selection).
_THEME_COMPONENT_HTML = """
<div class="goat-theme-btns">
  <button type="button" class="goat-tbtn" onclick="window.goatSetTheme('Light')">Light</button>
  <button type="button" class="goat-tbtn" onclick="window.goatSetTheme('Dark')">Dark</button>
  <button type="button" class="goat-tbtn" onclick="window.goatSetTheme('System')">System</button>
</div>
<style>
  .goat-theme-btns { display: flex; flex-wrap: wrap; gap: 0.4rem; justify-content: stretch; }
    .goat-tbtn {
    flex: 1 1 30%;
    min-width: 4.5rem;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.45rem 0.35rem;
    border-radius: 6px;
      border: 1px solid #003A70;
    background: #FFCD00;
      color: #003A70;
  }
  .goat-tbtn:hover { filter: brightness(1.05); }
  .goat-tbtn:active { filter: brightness(0.95); }
</style>
<script>
(function () {
  window.goatSetTheme = function (mode) {
    try {
      var w = window.parent;
      var k = "stActiveTheme-" + w.location.pathname + "-v2";
      w.localStorage.setItem(k, JSON.stringify(mode));
      w.location.reload();
    } catch (e) {
      console.error(e);
    }
  };
})();
</script>
"""


def render_theme_switcher() -> None:
    """Embed Light / Dark / System controls (persists like the main app theme menu)."""
    components.html(_THEME_COMPONENT_HTML, height=52)
