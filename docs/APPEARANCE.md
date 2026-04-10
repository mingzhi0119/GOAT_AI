# GOAT AI Appearance System

Last updated: 2026-04-10

This document is the durable hand-off for the frontend appearance system added in Phase 16 planning follow-up work. It is written for both human contributors and coding agents so they can change the UI without reverse-engineering theme behavior from scattered components.

## Purpose

GOAT AI now uses a token-driven appearance system modeled after Codex-style desktop settings rather than a binary light/dark toggle.

The system goals are:

- centralize visual state at the document root
- keep component styling semantic and token-based
- support multiple named product skins
- persist user preferences locally without backend changes
- avoid first-paint theme flicker
- make future theme work extendable without rewriting the app shell

## User-visible behavior

The current frontend supports these appearance controls:

- `themeMode`: `light`, `dark`, `system`
- `themeStyle`: `classic`, `urochester`, `thu`
- `accentColor`: hex color, curated presets plus validated custom value
- `uiFont`: curated UI font stacks
- `codeFont`: curated monospace stacks
- `contrast`: integer slider used to strengthen borders, muted text separation, and selected surfaces
- `translucentSidebar`: glass treatment for sidebar/menu surfaces

Current shipped theme behavior also includes:

- `Classic` defaults to a blue accent, pure-white chat surface, and a slightly gray-white sidebar
- all three styles (`classic`, `urochester`, `thu`) apply the active accent color to the user bubble / send-action family
- the sidebar footer logo is style-specific: no school logo for `classic`, Rochester logo for `urochester`, and Tsinghua logo for `thu`
- dark mode inverts the school-mark treatment for readability; Tsinghua uses a white-reversed rendering in dark mode
- history rows use a denser list layout and only the active conversation receives the filled container treatment

The settings entry point is:

- top bar `Options` -> `Appearance` -> dedicated modal panel

The panel is preview-first:

- changes apply immediately to the live app
- the modal contains an embedded preview, but the real shell also updates at once
- preferences persist to `localStorage`
- `Reset defaults` restores the canonical config

## Source of truth

Main implementation files:

- `frontend/src/utils/appearance.ts`
- `frontend/src/hooks/useAppearance.tsx`
- `frontend/src/components/AppearancePanel.tsx`
- `frontend/src/components/TopBar.tsx`
- `frontend/src/styles/global.css`
- `frontend/index.html`

Supporting integration points:

- `frontend/src/App.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/MessageBubble.tsx`
- `frontend/src/__tests__/appearance.test.ts`
- `frontend/src/__tests__/AppearancePanel.test.tsx`
- `frontend/src/__tests__/TopBar.test.tsx`

## Architecture

### 1. Appearance config model

`appearance.ts` owns the typed model:

- `AppearanceConfig`
- `AppearanceMode`
- `ResolvedThemeMode`
- `AppearanceStyleId`
- `UIFontId`
- `CodeFontId`
- `ThemeTokenSet`
- `ThemeStyleDefinition`

`DEFAULT_APPEARANCE_CONFIG` is the canonical default and should be updated deliberately when the product baseline changes.

### 2. Theme registry

The registry lives in `THEME_STYLES` inside `appearance.ts`.

Each style defines:

- metadata: id, label, description
- curated accent presets
- token sets for both resolved light and resolved dark modes

Important rule:

- component code should consume semantic CSS vars such as `--bg-chat` or `--text-muted`
- component code should not branch on `classic` vs `thu` directly unless the UI behavior itself differs

Current exception:

- `Sidebar` legitimately branches on `themeStyle` for footer logo selection because the rendered asset itself differs by style

### 3. Root application of tokens

`applyAppearanceToRoot()` is the central bridge from typed config to CSS variables.

It applies:

- root datasets:
  - `data-theme-mode`
  - `data-theme-resolved`
  - `data-theme-style`
  - `data-sidebar-translucent`
- root custom properties for:
  - semantic surfaces
  - semantic text colors
  - borders and input surfaces
  - accent colors
  - UI/code font families
  - code block and prose support tokens

This keeps theming centralized and avoids per-component class branching.

### 4. Persistence and migration

Persistence is frontend-only.

- storage key: `goat-ai-appearance`
- legacy migration: `goat-ai-theme`

`loadStoredAppearance()` loads the new config if present, otherwise migrates the old light/dark value into the new model.

### 5. Anti-flicker startup

`frontend/index.html` contains a small bootstrap script that:

- reads stored appearance values before React mounts
- resolves `system` mode using `matchMedia`
- sets early root datasets and a minimal token subset

React then hydrates the full token set through `AppearanceProvider`.

## Component rules

When updating frontend visuals, prefer these rules:

- use existing semantic CSS vars before inventing new ones
- add new tokens in `appearance.ts` plus `global.css` only when a real semantic gap exists
- keep components style-agnostic; do not hardcode theme-style ids into normal UI rendering
- add preview-only structure inside `AppearancePanel`, not in unrelated app components
- if a new appearance control changes persisted state, model it in `AppearanceConfig` first

Additional UI behavior rules:

- `Thinking` traces may still arrive over SSE even when the user has thinking disabled; the UI must hide the disclosure unless the message was created with thinking enabled
- do not emit sidebar delete affordances on keyboard focus alone; hover-only reveal avoids accidental white overlay artifacts in the history list
- keep theme cards top-aligned in `AppearancePanel`; shorter descriptions such as `Classic` should not vertically center while longer descriptions wrap

## Max tokens UX rule

Generation settings intentionally do not warn when the user enters a `max_tokens` value above the API ceiling.

Current behavior:

- input is silently clamped to the API maximum (`131072`)
- no explanatory helper text is shown below the field

This is a deliberate product choice to keep the settings panel compact and low-friction.

## Testing expectations

When appearance behavior changes, cover at least:

- config sanitization and migration
- root token application
- top-bar entry wiring
- appearance modal interactions
- persistence-related behavior when applicable

Current automated coverage includes:

- `appearance.test.ts`
- `AppearancePanel.test.tsx`
- updated `TopBar.test.tsx`
- `Sidebar.test.tsx`
- `MessageBubble.test.tsx`

For layout-affecting changes, still follow the manual verification loop from `docs/ENGINEERING_STANDARDS.md`.

## Safe extension patterns

If you add a new theme style:

1. add a new `AppearanceStyleId`
2. add a new `ThemeStyleDefinition` with both light and dark token sets
3. provide curated accent presets
4. ensure `AppearancePanel` exposes the style card
5. verify existing shell surfaces stay readable in both widths

If you add a new control:

1. extend `AppearanceConfig`
2. sanitize and persist it
3. apply it through root tokens or root datasets
4. add targeted tests
5. document the new behavior here

## Things to avoid

- do not reintroduce a standalone `.dark` class toggle as the primary theme system
- do not scatter raw theme hex values across components
- do not read `localStorage` directly from random UI components for appearance state
- do not add backend persistence for appearance without a strong product requirement
- do not bypass `applyAppearanceToRoot()` for app-wide visual behavior
