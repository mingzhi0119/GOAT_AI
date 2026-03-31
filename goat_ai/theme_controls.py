"""Floating Light / Dark theme switcher injected into the Streamlit header bar.

Uses onclick handlers (main-page context) to write Streamlit's own localStorage
key and reload, which is identical to what the built-in Settings → Theme menu does.

Inject via ``st.html(..., unsafe_allow_javascript=True)`` — not ``st.markdown``, or
onclick is misparsed and markup leaks as visible text at the top of the page.
"""

from __future__ import annotations

# Streamlit stores the active theme under  stActiveTheme-{pathname}-v2  as a
# JSON-encoded string, e.g. '"Light"' or '"Dark"'.  We write the same keys that
# Streamlit's own frontend reads on startup, so the change persists across reloads.
FLOATING_THEME_HTML = """
<div id="goat-theme-bar" style="
  position: fixed;
  top: 8px;
  right: 52px;
  z-index: 99999;
  display: flex;
  gap: 5px;
  align-items: center;
">
  <button
    title="Switch to Light mode"
    onclick="(function(){
      var path = window.location.pathname;
      var val  = JSON.stringify('Light');
      ['stActiveTheme-'+path+'-v2',
       'stActiveTheme-'+path.replace(/\\/$/,'')+'-v2',
       'stActiveTheme'].forEach(function(k){ localStorage.setItem(k, val); });
      location.reload();
    })();"
    style="
      background:#FFCD00;
      color:#003A70;
      border:2px solid #003A70;
      border-radius:6px;
      padding:3px 11px;
      font-size:0.78rem;
      font-weight:700;
      cursor:pointer;
      line-height:1.5;
      white-space:nowrap;
    "
  >☀️ Light</button>

  <button
    title="Switch to Dark mode"
    onclick="(function(){
      var path = window.location.pathname;
      var val  = JSON.stringify('Dark');
      ['stActiveTheme-'+path+'-v2',
       'stActiveTheme-'+path.replace(/\\/$/,'')+'-v2',
       'stActiveTheme'].forEach(function(k){ localStorage.setItem(k, val); });
      location.reload();
    })();"
    style="
      background:#003A70;
      color:#FFCD00;
      border:2px solid #FFCD00;
      border-radius:6px;
      padding:3px 11px;
      font-size:0.78rem;
      font-weight:700;
      cursor:pointer;
      line-height:1.5;
      white-space:nowrap;
    "
  >🌙 Dark</button>
</div>
"""
