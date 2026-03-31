/**
 * Shared Tailwind class tokens for non-interactive sidebar copy.
 * Keeps selection/cursor behavior consistent (no I-beam on static labels).
 */

const nonInteractive = 'select-none cursor-default'

/** Section titles like YOUR NAME, MODEL, HISTORY (with bottom margin). */
export const sidebarSectionLabelClass = `text-xs font-semibold uppercase tracking-wider mb-2 ${nonInteractive}`

/** Section title in a flex row without bottom margin (e.g. History header). */
export const sidebarSectionLabelRowClass = `text-xs font-semibold uppercase tracking-wider ${nonInteractive}`

/** Logo title line. */
export const sidebarBrandTitleClass = `font-extrabold text-lg leading-tight ${nonInteractive}`

/** Logo subtitle / secondary line. */
export const sidebarBrandSubtitleClass = `text-xs leading-tight ${nonInteractive}`

/** Muted helper lines (loading, empty state). */
export const sidebarHelperMutedClass = `text-xs mb-1 ${nonInteractive}`

/** Error helper under controls. */
export const sidebarErrorTextClass = `text-xs mt-1 ${nonInteractive}`

/** Footer attribution paragraph. */
export const sidebarFooterAttributionClass = `text-xs ${nonInteractive}`

/** Inline gold name inside footer (still non-selectable). */
export const sidebarFooterHighlightClass = nonInteractive

/** Filename chip text (read-only). */
export const sidebarFileChipNameClass = `truncate ${nonInteractive}`

/** Re-export base token for one-off composition (e.g. inside buttons). */
export const sidebarStaticBaseClass = nonInteractive
