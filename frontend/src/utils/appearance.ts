import {
  CODE_FONT_OPTIONS as CODE_FONT_OPTION_ASSETS,
  THEME_STYLES as THEME_STYLE_ASSETS,
  UI_FONT_OPTIONS as UI_FONT_OPTION_ASSETS,
} from '../assets/appearanceThemeAssets'

export type AppearanceMode = 'light' | 'dark' | 'system'
export type ResolvedThemeMode = 'light' | 'dark'
export type AppearanceStyleId = 'classic' | 'urochester' | 'thu'
export type UIFontId = 'inter' | 'system-sans' | 'humanist'
export type CodeFontId = 'jetbrains' | 'sfmono' | 'mono'

export interface AppearanceConfig {
  themeMode: AppearanceMode
  themeStyle: AppearanceStyleId
  accentColor: string
  uiFont: UIFontId
  codeFont: CodeFontId
  contrast: number
  translucentSidebar: boolean
}

export interface FontOption<TId extends string> {
  id: TId
  label: string
  cssValue: string
}

export interface ThemeTokenSet {
  mainBg: string
  sidebarBg: string
  chatBg: string
  userBubbleBg: string
  assistantBubbleBg: string
  panelBg: string
  panelBgStrong: string
  textMain: string
  textMuted: string
  textSidebar: string
  textUserBubble: string
  textAssistantBubble: string
  borderColor: string
  inputBg: string
  inputBorder: string
  scrollbarThumb: string
  sidebarHover: string
  sidebarSurface: string
  sidebarSurfaceMuted: string
  sidebarBorder: string
  sidebarMuted: string
  sidebarDanger: string
  sidebarDangerBg: string
  composerMutedSurface: string
  composerSelectedSurface: string
  composerChipBorder: string
  composerDangerText: string
  composerDangerBorder: string
  composerDangerBg: string
  composerDangerFg: string
  composerControlIcon: string
  composerControlHoverBg: string
  composerPillOpenShadow: string
  composerSendBg: string
  composerSendFg: string
  composerSendDisabledBg: string
  goatIconFrameBg: string
  goatIconCircleBg: string
  codeInlineBg: string
  codeBlockBg: string
  tableHeaderBg: string
  blockquoteBorder: string
  linkColor: string
  assistantHover: string
  previewCodeA: string
  previewCodeB: string
  previewDiffRemoved: string
  previewDiffAdded: string
  shadowColor: string
}

export interface ThemeStyleDefinition {
  id: AppearanceStyleId
  label: string
  description: string
  accentPresets: string[]
  tokens: Record<ResolvedThemeMode, ThemeTokenSet>
}

export const APPEARANCE_STORAGE_KEY = 'goat-ai-appearance'
const LEGACY_THEME_STORAGE_KEY = 'goat-ai-theme'

const clampContrast = (value: number): number => Math.max(0, Math.min(100, Math.round(value)))

const rgba = (r: number, g: number, b: number, a: number): string => `rgba(${r}, ${g}, ${b}, ${a})`

export const UI_FONT_OPTIONS: FontOption<UIFontId>[] = UI_FONT_OPTION_ASSETS
export const CODE_FONT_OPTIONS: FontOption<CodeFontId>[] = CODE_FONT_OPTION_ASSETS
export const THEME_STYLES: ThemeStyleDefinition[] = THEME_STYLE_ASSETS

export const DEFAULT_APPEARANCE_CONFIG: AppearanceConfig = {
  themeMode: 'system',
  themeStyle: 'classic',
  accentColor: '#2563eb',
  uiFont: 'inter',
  codeFont: 'jetbrains',
  contrast: 45,
  translucentSidebar: true,
}

const THEME_STYLE_MAP = Object.fromEntries(
  THEME_STYLES.map(style => [style.id, style]),
) as Record<AppearanceStyleId, ThemeStyleDefinition>

const UI_FONT_MAP = Object.fromEntries(
  UI_FONT_OPTIONS.map(option => [option.id, option]),
) as Record<UIFontId, FontOption<UIFontId>>

const CODE_FONT_MAP = Object.fromEntries(
  CODE_FONT_OPTIONS.map(option => [option.id, option]),
) as Record<CodeFontId, FontOption<CodeFontId>>

function isAppearanceMode(value: unknown): value is AppearanceMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

function isAppearanceStyleId(value: unknown): value is AppearanceStyleId {
  return value === 'classic' || value === 'urochester' || value === 'thu'
}

function isUIFontId(value: unknown): value is UIFontId {
  return value === 'inter' || value === 'system-sans' || value === 'humanist'
}

function isCodeFontId(value: unknown): value is CodeFontId {
  return value === 'jetbrains' || value === 'sfmono' || value === 'mono'
}

function normalizeHexColor(value: unknown, fallback: string): string {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  if (/^#[0-9a-f]{6}$/i.test(trimmed)) return trimmed.toLowerCase()
  return fallback
}

function expandHexColor(value: string): string | null {
  const trimmed = value.trim()
  const hex = trimmed.startsWith('#') ? trimmed.slice(1) : trimmed
  if (/^[0-9a-f]{3}$/i.test(hex)) {
    return `#${hex
      .split('')
      .map(channel => `${channel}${channel}`)
      .join('')}`
  }
  if (/^[0-9a-f]{6}$/i.test(hex)) {
    return `#${hex}`.toLowerCase()
  }
  if (/^[0-9a-f]{8}$/i.test(hex)) {
    const rgb = `#${hex.slice(0, 6)}`
    return rgb.toLowerCase()
  }
  return null
}

function parseRgb(value: string): [number, number, number] {
  const normalized = value.replace('#', '')
  const r = Number.parseInt(normalized.slice(0, 2), 16)
  const g = Number.parseInt(normalized.slice(2, 4), 16)
  const b = Number.parseInt(normalized.slice(4, 6), 16)
  return [r, g, b]
}

function parseHexAlpha(value: string): number | null {
  const trimmed = value.trim()
  const hex = trimmed.startsWith('#') ? trimmed.slice(1) : trimmed
  if (/^[0-9a-f]{8}$/i.test(hex)) {
    return Number.parseInt(hex.slice(6, 8), 16) / 255
  }
  if (/^[0-9a-f]{4}$/i.test(hex)) {
    return Number.parseInt(hex.slice(3, 4).repeat(2), 16) / 255
  }
  return null
}

function parseCssColor(value: string): { hex: string; alpha: number | null } | null {
  const expandedHex = expandHexColor(value)
  if (expandedHex) {
    return { hex: expandedHex.toUpperCase(), alpha: parseHexAlpha(value) }
  }

  const rgbaMatch = value
    .trim()
    .match(
      /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([0-9.]+)\s*)?\)$/i,
    )
  if (!rgbaMatch) return null

  const r = Number.parseInt(rgbaMatch[1] ?? '', 10)
  const g = Number.parseInt(rgbaMatch[2] ?? '', 10)
  const b = Number.parseInt(rgbaMatch[3] ?? '', 10)
  if (
    [r, g, b].some(channel => Number.isNaN(channel) || channel < 0 || channel > 255)
  ) {
    return null
  }

  const hex = `#${[r, g, b]
    .map(channel => channel.toString(16).padStart(2, '0'))
    .join('')}`.toUpperCase()
  const alpha = rgbaMatch[4] === undefined ? null : Number.parseFloat(rgbaMatch[4])
  return {
    hex,
    alpha: alpha !== null && !Number.isNaN(alpha) ? alpha : null,
  }
}

export function formatColorTokenDisplay(value: string): string {
  const parsed = parseCssColor(value)
  if (!parsed) return value
  if (parsed.alpha === null || parsed.alpha <= 0 || parsed.alpha >= 1) {
    return parsed.hex
  }

  const percent = Math.round(parsed.alpha * 100)
  return `${parsed.hex}, ${percent}%`
}

function colorMix(hex: string, target: string, ratio: number): string {
  const [r1, g1, b1] = parseRgb(hex)
  const [r2, g2, b2] = parseRgb(target)
  const mix = (a: number, b: number) => Math.round(a + (b - a) * ratio)
  return `#${[mix(r1, r2), mix(g1, g2), mix(b1, b2)]
    .map(channel => channel.toString(16).padStart(2, '0'))
    .join('')}`
}

function getAccentForeground(hex: string): string {
  const [r, g, b] = parseRgb(hex)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness > 150 ? '#111827' : '#ffffff'
}

function getThemeStyleDefinition(styleId: AppearanceStyleId): ThemeStyleDefinition {
  return THEME_STYLE_MAP[styleId]
}

export function resolveThemeMode(mode: AppearanceMode, prefersDark: boolean): ResolvedThemeMode {
  return mode === 'system' ? (prefersDark ? 'dark' : 'light') : mode
}

export function getSystemPrefersDark(): boolean {
  return typeof window !== 'undefined'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false
}

export function sanitizeAppearanceConfig(raw: unknown): AppearanceConfig {
  const input =
    raw && typeof raw === 'object' ? (raw as Partial<Record<keyof AppearanceConfig, unknown>>) : {}
  return {
    themeMode: isAppearanceMode(input.themeMode)
      ? input.themeMode
      : DEFAULT_APPEARANCE_CONFIG.themeMode,
    themeStyle: isAppearanceStyleId(input.themeStyle)
      ? input.themeStyle
      : DEFAULT_APPEARANCE_CONFIG.themeStyle,
    accentColor: normalizeHexColor(input.accentColor, DEFAULT_APPEARANCE_CONFIG.accentColor),
    uiFont: isUIFontId(input.uiFont) ? input.uiFont : DEFAULT_APPEARANCE_CONFIG.uiFont,
    codeFont: isCodeFontId(input.codeFont) ? input.codeFont : DEFAULT_APPEARANCE_CONFIG.codeFont,
    contrast:
      typeof input.contrast === 'number'
        ? clampContrast(input.contrast)
        : DEFAULT_APPEARANCE_CONFIG.contrast,
    translucentSidebar:
      typeof input.translucentSidebar === 'boolean'
        ? input.translucentSidebar
        : DEFAULT_APPEARANCE_CONFIG.translucentSidebar,
  }
}

export function loadStoredAppearance(
  storage: Pick<Storage, 'getItem' | 'removeItem'>,
): AppearanceConfig {
  const raw = storage.getItem(APPEARANCE_STORAGE_KEY)
  if (raw) {
    try {
      return sanitizeAppearanceConfig(JSON.parse(raw))
    } catch {
      storage.removeItem(APPEARANCE_STORAGE_KEY)
    }
  }

  const legacyTheme = storage.getItem(LEGACY_THEME_STORAGE_KEY)
  if (legacyTheme === 'light' || legacyTheme === 'dark') {
    return {
      ...DEFAULT_APPEARANCE_CONFIG,
      themeMode: legacyTheme,
    }
  }

  return DEFAULT_APPEARANCE_CONFIG
}

export function persistAppearanceConfig(
  storage: Pick<Storage, 'setItem' | 'removeItem'>,
  config: AppearanceConfig,
): void {
  storage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(config))
  storage.removeItem(LEGACY_THEME_STORAGE_KEY)
}

function withContrastAlpha(baseAlpha: number, contrast: number, minBoost: number): number {
  return Math.min(1, Math.max(0, baseAlpha + minBoost + contrast / 220))
}

function extractFirstAlpha(rgbaValue: string, fallback: number): number {
  const match = rgbaValue.match(
    /rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)/i,
  )
  return match ? Number.parseFloat(match[1] ?? `${fallback}`) : fallback
}

export function getComputedThemeTokens(
  config: AppearanceConfig,
  prefersDark: boolean,
): ThemeTokenSet {
  const resolvedMode = resolveThemeMode(config.themeMode, prefersDark)
  const styleTokens = getThemeStyleDefinition(config.themeStyle).tokens[resolvedMode]
  const contrast = clampContrast(config.contrast)

  const borderBase = extractFirstAlpha(
    styleTokens.borderColor,
    resolvedMode === 'dark' ? 0.09 : 0.08,
  )
  const inputBorderBase = extractFirstAlpha(
    styleTokens.inputBorder,
    resolvedMode === 'dark' ? 0.09 : 0.08,
  )
  const sidebarBorderBase = extractFirstAlpha(
    styleTokens.sidebarBorder,
    resolvedMode === 'dark' ? 0.11 : 0.08,
  )
  const sidebarSurfaceBase = extractFirstAlpha(
    styleTokens.sidebarSurface,
    resolvedMode === 'dark' ? 0.08 : 0.86,
  )
  const sidebarSurfaceMutedBase = extractFirstAlpha(
    styleTokens.sidebarSurfaceMuted,
    resolvedMode === 'dark' ? 0.06 : 0.72,
  )

  const accent = normalizeHexColor(
    config.accentColor,
    DEFAULT_APPEARANCE_CONFIG.accentColor,
  )
  const accentStrong =
    resolvedMode === 'dark'
      ? colorMix(accent, '#ffffff', 0.16)
      : colorMix(accent, '#0f172a', 0.12)
  const accentSoft = rgba(...parseRgb(accent), resolvedMode === 'dark' ? 0.22 : 0.14)
  const accentSofter = rgba(...parseRgb(accent), resolvedMode === 'dark' ? 0.14 : 0.08)
  const accentForeground = getAccentForeground(accent)

  const sidebarAlpha = config.translucentSidebar
    ? Math.max(0.48, sidebarSurfaceBase)
    : Math.min(1, sidebarSurfaceBase + 0.12)
  const sidebarMutedAlpha = config.translucentSidebar
    ? Math.max(0.38, sidebarSurfaceMutedBase)
    : Math.min(1, sidebarSurfaceMutedBase + 0.14)

  return {
    ...styleTokens,
    userBubbleBg: accent,
    textUserBubble: accentForeground,
    borderColor:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, withContrastAlpha(borderBase, contrast, 0))
        : rgba(18, 24, 38, withContrastAlpha(borderBase, contrast, 0)),
    inputBorder:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, withContrastAlpha(inputBorderBase, contrast, 0.01))
        : rgba(18, 24, 38, withContrastAlpha(inputBorderBase, contrast, 0.01)),
    sidebarBorder:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, withContrastAlpha(sidebarBorderBase, contrast, 0.01))
        : rgba(18, 24, 38, withContrastAlpha(sidebarBorderBase, contrast, 0.01)),
    sidebarSurface: rgba(255, 255, 255, sidebarAlpha),
    sidebarSurfaceMuted: rgba(255, 255, 255, sidebarMutedAlpha),
    textMuted:
      resolvedMode === 'dark'
        ? colorMix(styleTokens.textMuted, '#ffffff', contrast / 500)
        : colorMix(styleTokens.textMuted, '#111827', contrast / 520),
    sidebarMuted:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, Math.min(0.82, 0.44 + contrast / 180))
        : colorMix(styleTokens.sidebarMuted, '#111827', contrast / 600),
    composerMutedSurface:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, 0.035 + contrast / 600)
        : rgba(15, 23, 42, 0.02 + contrast / 700),
    composerSelectedSurface:
      resolvedMode === 'dark'
        ? rgba(...parseRgb(accent), 0.15 + contrast / 600)
        : rgba(...parseRgb(accent), 0.10 + contrast / 650),
    composerChipBorder:
      resolvedMode === 'dark'
        ? rgba(...parseRgb(accentStrong), 0.22)
        : rgba(...parseRgb(accentStrong), 0.18),
    composerControlHoverBg: accentSofter,
    composerPillOpenShadow: `0 14px 34px ${styleTokens.shadowColor}`,
    composerSendBg: accent,
    composerSendFg: accentForeground,
    composerSendDisabledBg:
      resolvedMode === 'dark'
        ? colorMix(accent, '#4b5563', 0.65)
        : colorMix(accent, '#cbd5e1', 0.62),
    linkColor: accentStrong,
    tableHeaderBg: accentSofter,
    codeInlineBg:
      resolvedMode === 'dark' ? accentSofter : rgba(...parseRgb(accent), 0.1),
    previewCodeA: accentStrong,
    previewCodeB:
      resolvedMode === 'dark'
        ? colorMix(accent, '#f8fafc', 0.34)
        : colorMix(accent, '#92400e', 0.28),
    previewDiffAdded:
      resolvedMode === 'dark' ? rgba(34, 197, 94, 0.22) : '#dff1e3',
    previewDiffRemoved:
      resolvedMode === 'dark' ? rgba(239, 68, 68, 0.22) : '#f8dfdb',
  }
}

export function applyAppearanceToRoot(
  root: HTMLElement,
  config: AppearanceConfig,
  prefersDark: boolean,
): void {
  const resolvedMode = resolveThemeMode(config.themeMode, prefersDark)
  const tokens = getComputedThemeTokens(config, prefersDark)
  const uiFont = UI_FONT_MAP[config.uiFont]
  const codeFont = CODE_FONT_MAP[config.codeFont]
  const accentRgb = parseRgb(config.accentColor)

  root.dataset.themeMode = config.themeMode
  root.dataset.themeResolved = resolvedMode
  root.dataset.themeStyle = config.themeStyle
  root.dataset.sidebarTranslucent = config.translucentSidebar ? 'true' : 'false'
  root.style.colorScheme = resolvedMode

  root.style.setProperty('--theme-accent', config.accentColor)
  root.style.setProperty('--theme-accent-strong', tokens.linkColor)
  root.style.setProperty(
    '--theme-accent-soft',
    rgba(
      accentRgb[0],
      accentRgb[1],
      accentRgb[2],
      resolvedMode === 'dark' ? 0.22 : 0.14,
    ),
  )
  root.style.setProperty(
    '--theme-accent-contrast',
    getAccentForeground(config.accentColor),
  )
  root.style.setProperty('--ui-font-family', uiFont.cssValue)
  root.style.setProperty('--code-font-family', codeFont.cssValue)
  root.style.setProperty('--contrast-strength', `${config.contrast}`)

  const entries: Array<[string, string]> = [
    ['--navy', tokens.textMain],
    ['--gold', config.accentColor],
    ['--bg-main', tokens.mainBg],
    ['--bg-sidebar', tokens.sidebarBg],
    ['--bg-chat', tokens.chatBg],
    ['--bg-user-bubble', tokens.userBubbleBg],
    ['--bg-asst-bubble', tokens.assistantBubbleBg],
    ['--text-main', tokens.textMain],
    ['--text-muted', tokens.textMuted],
    ['--text-sidebar', tokens.textSidebar],
    ['--text-user-bubble', tokens.textUserBubble],
    ['--text-asst-bubble', tokens.textAssistantBubble],
    ['--border-color', tokens.borderColor],
    ['--input-bg', tokens.inputBg],
    ['--input-border', tokens.inputBorder],
    ['--scrollbar-thumb', tokens.scrollbarThumb],
    ['--scrollbar-track', 'transparent'],
    ['--sidebar-hover', tokens.sidebarHover],
    ['--sidebar-surface', tokens.sidebarSurface],
    ['--sidebar-surface-muted', tokens.sidebarSurfaceMuted],
    ['--sidebar-border', tokens.sidebarBorder],
    ['--sidebar-muted', tokens.sidebarMuted],
    ['--sidebar-danger', tokens.sidebarDanger],
    ['--sidebar-danger-bg', tokens.sidebarDangerBg],
    [
      '--composer-surface',
      `linear-gradient(180deg, ${tokens.panelBgStrong} 0%, ${tokens.panelBg} 100%)`,
    ],
    ['--composer-menu-bg', tokens.panelBg],
    ['--composer-menu-bg-strong', tokens.panelBgStrong],
    ['--composer-muted-surface', tokens.composerMutedSurface],
    ['--composer-selected-surface', tokens.composerSelectedSurface],
    ['--composer-chip-border', tokens.composerChipBorder],
    ['--composer-danger-text', tokens.composerDangerText],
    ['--composer-danger-border', tokens.composerDangerBorder],
    ['--composer-danger-bg', tokens.composerDangerBg],
    ['--composer-danger-fg', tokens.composerDangerFg],
    ['--composer-control-icon', tokens.composerControlIcon],
    ['--composer-control-hover-bg', tokens.composerControlHoverBg],
    ['--composer-pill-open-shadow', tokens.composerPillOpenShadow],
    ['--composer-send-bg', tokens.composerSendBg],
    ['--composer-send-fg', tokens.composerSendFg],
    ['--composer-send-disabled-bg', tokens.composerSendDisabledBg],
    ['--goat-icon-frame-bg', tokens.goatIconFrameBg],
    ['--goat-icon-circle-bg', tokens.goatIconCircleBg],
    ['--code-inline-bg', tokens.codeInlineBg],
    ['--code-block-bg', tokens.codeBlockBg],
    ['--table-header-bg', tokens.tableHeaderBg],
    ['--blockquote-border', tokens.blockquoteBorder],
    ['--link-color', tokens.linkColor],
    ['--assistant-hover', tokens.assistantHover],
    ['--panel-shadow-color', tokens.shadowColor],
    ['--preview-code-a', tokens.previewCodeA],
    ['--preview-code-b', tokens.previewCodeB],
    ['--preview-diff-removed', tokens.previewDiffRemoved],
    ['--preview-diff-added', tokens.previewDiffAdded],
  ]

  for (const [key, value] of entries) {
    root.style.setProperty(key, value)
  }
}

export function getThemeStyleLabel(styleId: AppearanceStyleId): string {
  return getThemeStyleDefinition(styleId).label
}

export function getAppearanceSummary(config: AppearanceConfig): string {
  const modeLabel = config.themeMode[0]!.toUpperCase() + config.themeMode.slice(1)
  return `${getThemeStyleLabel(config.themeStyle)} / ${modeLabel}`
}

export function getStyleAccentPresets(styleId: AppearanceStyleId): string[] {
  return getThemeStyleDefinition(styleId).accentPresets
}
