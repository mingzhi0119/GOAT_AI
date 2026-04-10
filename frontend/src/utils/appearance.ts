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

const buildClassicTokens = (): Record<ResolvedThemeMode, ThemeTokenSet> => ({
  light: {
    mainBg: '#f7f7f8',
    sidebarBg: '#f4f4f5',
    chatBg: '#ffffff',
    userBubbleBg: '#17181c',
    assistantBubbleBg: '#ffffff',
    panelBg: 'rgba(255, 255, 255, 0.92)',
    panelBgStrong: 'rgba(255, 255, 255, 0.98)',
    textMain: '#16181d',
    textMuted: '#6b7280',
    textSidebar: '#1d2128',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#16181d',
    borderColor: 'rgba(18, 24, 38, 0.08)',
    inputBg: '#ffffff',
    inputBorder: 'rgba(18, 24, 38, 0.08)',
    scrollbarThumb: '#d1d5db',
    sidebarHover: 'rgba(18, 24, 38, 0.04)',
    sidebarSurface: 'rgba(255, 255, 255, 0.92)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.82)',
    sidebarBorder: 'rgba(18, 24, 38, 0.08)',
    sidebarMuted: '#6b7280',
    sidebarDanger: '#b91c1c',
    sidebarDangerBg: 'rgba(185, 28, 28, 0.08)',
    composerMutedSurface: 'rgba(15, 23, 42, 0.028)',
    composerSelectedSurface: 'rgba(15, 23, 42, 0.075)',
    composerChipBorder: 'rgba(0, 0, 0, 0.12)',
    composerDangerText: '#b91c1c',
    composerDangerBorder: 'rgba(239, 68, 68, 0.28)',
    composerDangerBg: 'rgba(239, 68, 68, 0.08)',
    composerDangerFg: '#fca5a5',
    composerControlIcon: 'rgba(17, 24, 39, 0.46)',
    composerControlHoverBg: 'rgba(17, 24, 39, 0.08)',
    composerPillOpenShadow: '0 10px 24px rgba(15, 23, 42, 0.10)',
    composerSendBg: '#17181c',
    composerSendFg: '#ffffff',
    composerSendDisabledBg: '#98a2b3',
    goatIconFrameBg: 'rgba(0, 0, 0, 0.06)',
    goatIconCircleBg: '#1a1b1f',
    codeInlineBg: 'rgba(15, 23, 42, 0.07)',
    codeBlockBg: '#0f172a',
    tableHeaderBg: 'rgba(15, 23, 42, 0.05)',
    blockquoteBorder: 'rgba(17, 24, 39, 0.18)',
    linkColor: '#2563eb',
    assistantHover: 'rgba(17, 24, 39, 0.022)',
    previewCodeA: '#7c3aed',
    previewCodeB: '#d97706',
    previewDiffRemoved: '#f6d8d2',
    previewDiffAdded: '#dceddd',
    shadowColor: 'rgba(15, 23, 42, 0.12)',
  },
  dark: {
    mainBg: '#0d1016',
    sidebarBg: '#0a0d12',
    chatBg: '#11151c',
    userBubbleBg: '#252b35',
    assistantBubbleBg: '#171b23',
    panelBg: 'rgba(17, 21, 28, 0.84)',
    panelBgStrong: 'rgba(17, 21, 28, 0.96)',
    textMain: '#f6f7fb',
    textMuted: '#a0a8b7',
    textSidebar: '#edf1f7',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#f6f7fb',
    borderColor: 'rgba(255, 255, 255, 0.09)',
    inputBg: 'rgba(20, 24, 33, 0.94)',
    inputBorder: 'rgba(255, 255, 255, 0.09)',
    scrollbarThumb: '#3b4453',
    sidebarHover: 'rgba(255, 255, 255, 0.055)',
    sidebarSurface: 'rgba(255, 255, 255, 0.08)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.06)',
    sidebarBorder: 'rgba(255, 255, 255, 0.11)',
    sidebarMuted: 'rgba(255, 255, 255, 0.56)',
    sidebarDanger: '#fca5a5',
    sidebarDangerBg: 'rgba(248, 113, 113, 0.14)',
    composerMutedSurface: 'rgba(255, 255, 255, 0.05)',
    composerSelectedSurface: 'rgba(255, 255, 255, 0.11)',
    composerChipBorder: 'rgba(255, 255, 255, 0.14)',
    composerDangerText: '#fca5a5',
    composerDangerBorder: 'rgba(248, 113, 113, 0.28)',
    composerDangerBg: 'rgba(248, 113, 113, 0.10)',
    composerDangerFg: '#fecaca',
    composerControlIcon: 'rgba(244, 244, 245, 0.58)',
    composerControlHoverBg: 'rgba(255, 255, 255, 0.10)',
    composerPillOpenShadow: '0 14px 32px rgba(0, 0, 0, 0.42)',
    composerSendBg: '#eceff5',
    composerSendFg: '#17181c',
    composerSendDisabledBg: '#4b5563',
    goatIconFrameBg: 'rgba(255, 255, 255, 0.1)',
    goatIconCircleBg: '#252d39',
    codeInlineBg: 'rgba(255, 255, 255, 0.12)',
    codeBlockBg: '#071120',
    tableHeaderBg: 'rgba(255, 255, 255, 0.05)',
    blockquoteBorder: 'rgba(255, 255, 255, 0.18)',
    linkColor: '#7cb5ff',
    assistantHover: 'rgba(255, 255, 255, 0.04)',
    previewCodeA: '#a78bfa',
    previewCodeB: '#fbbf24',
    previewDiffRemoved: '#4f2b2a',
    previewDiffAdded: '#233f2d',
    shadowColor: 'rgba(0, 0, 0, 0.46)',
  },
})

const buildRochesterTokens = (): Record<ResolvedThemeMode, ThemeTokenSet> => ({
  light: {
    mainBg: '#f4f6fa',
    sidebarBg: '#ebf0f7',
    chatBg: '#f8fafd',
    userBubbleBg: '#001e5f',
    assistantBubbleBg: '#ffffff',
    panelBg: 'rgba(255, 255, 255, 0.88)',
    panelBgStrong: 'rgba(255, 255, 255, 0.97)',
    textMain: '#0f172a',
    textMuted: '#64748b',
    textSidebar: '#1e293b',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#0f172a',
    borderColor: 'rgba(0, 30, 95, 0.08)',
    inputBg: 'rgba(255, 255, 255, 0.94)',
    inputBorder: 'rgba(0, 30, 95, 0.10)',
    scrollbarThumb: 'rgba(0, 30, 95, 0.15)',
    sidebarHover: 'rgba(0, 30, 95, 0.04)',
    sidebarSurface: 'rgba(255, 255, 255, 0.84)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.72)',
    sidebarBorder: 'rgba(0, 30, 95, 0.10)',
    sidebarMuted: '#64748b',
    sidebarDanger: '#b91c1c',
    sidebarDangerBg: 'rgba(185, 28, 28, 0.08)',
    composerMutedSurface: 'rgba(0, 30, 95, 0.04)',
    composerSelectedSurface: 'rgba(0, 30, 95, 0.08)',
    composerChipBorder: 'rgba(0, 30, 95, 0.12)',
    composerDangerText: '#b91c1c',
    composerDangerBorder: 'rgba(239, 68, 68, 0.28)',
    composerDangerBg: 'rgba(239, 68, 68, 0.08)',
    composerDangerFg: '#fca5a5',
    composerControlIcon: 'rgba(0, 30, 95, 0.45)',
    composerControlHoverBg: 'rgba(0, 30, 95, 0.08)',
    composerPillOpenShadow: '0 12px 26px rgba(0, 30, 95, 0.12)',
    composerSendBg: '#001e5f',
    composerSendFg: '#ffffff',
    composerSendDisabledBg: '#94a3b8',
    goatIconFrameBg: 'rgba(0, 30, 95, 0.08)',
    goatIconCircleBg: '#001e5f',
    codeInlineBg: 'rgba(0, 30, 95, 0.06)',
    codeBlockBg: '#06132b',
    tableHeaderBg: 'rgba(0, 30, 95, 0.06)',
    blockquoteBorder: 'rgba(0, 30, 95, 0.20)',
    linkColor: '#003eff',
    assistantHover: 'rgba(0, 30, 95, 0.02)',
    previewCodeA: '#003eff',
    previewCodeB: '#ffd82b',
    previewDiffRemoved: '#fee4e2',
    previewDiffAdded: '#d1fadf',
    shadowColor: 'rgba(0, 30, 95, 0.12)',
  },
  dark: {
    mainBg: '#0b101e',
    sidebarBg: '#070a14',
    chatBg: '#0e1526',
    userBubbleBg: '#1e3a75',
    assistantBubbleBg: '#131e36',
    panelBg: 'rgba(12, 19, 36, 0.84)',
    panelBgStrong: 'rgba(12, 19, 36, 0.96)',
    textMain: '#f5f7fb',
    textMuted: '#94a3b8',
    textSidebar: '#e2e8f0',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#f5f7fb',
    borderColor: 'rgba(255, 255, 255, 0.12)',
    inputBg: 'rgba(19, 30, 54, 0.94)',
    inputBorder: 'rgba(255, 255, 255, 0.12)',
    scrollbarThumb: 'rgba(255, 255, 255, 0.18)',
    sidebarHover: 'rgba(255, 255, 255, 0.06)',
    sidebarSurface: 'rgba(255, 255, 255, 0.10)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.08)',
    sidebarBorder: 'rgba(255, 255, 255, 0.12)',
    sidebarMuted: 'rgba(255, 255, 255, 0.55)',
    sidebarDanger: '#fda4af',
    sidebarDangerBg: 'rgba(248, 113, 113, 0.12)',
    composerMutedSurface: 'rgba(255, 255, 255, 0.06)',
    composerSelectedSurface: 'rgba(255, 255, 255, 0.12)',
    composerChipBorder: 'rgba(255, 255, 255, 0.14)',
    composerDangerText: '#fda4af',
    composerDangerBorder: 'rgba(248, 113, 113, 0.28)',
    composerDangerBg: 'rgba(248, 113, 113, 0.10)',
    composerDangerFg: '#fecaca',
    composerControlIcon: 'rgba(255, 255, 255, 0.55)',
    composerControlHoverBg: 'rgba(255, 255, 255, 0.12)',
    composerPillOpenShadow: '0 14px 34px rgba(0, 0, 0, 0.5)',
    composerSendBg: '#ffd82b',
    composerSendFg: '#001e5f',
    composerSendDisabledBg: '#475569',
    goatIconFrameBg: 'rgba(255, 255, 255, 0.12)',
    goatIconCircleBg: '#1e3a75',
    codeInlineBg: 'rgba(255, 255, 255, 0.12)',
    codeBlockBg: '#050812',
    tableHeaderBg: 'rgba(255, 255, 255, 0.08)',
    blockquoteBorder: 'rgba(255, 255, 255, 0.20)',
    linkColor: '#ffd82b',
    assistantHover: 'rgba(255, 255, 255, 0.04)',
    previewCodeA: '#0066fd',
    previewCodeB: '#ffd82b',
    previewDiffRemoved: '#4e282b',
    previewDiffAdded: '#223d2d',
    shadowColor: 'rgba(0, 0, 0, 0.5)',
  },
})

const buildThuTokens = (): Record<ResolvedThemeMode, ThemeTokenSet> => ({
  light: {
    mainBg: '#f8f6f9',
    sidebarBg: '#f2eef4',
    chatBg: '#fcfafc',
    userBubbleBg: '#660874',
    assistantBubbleBg: '#ffffff',
    panelBg: 'rgba(255, 255, 255, 0.88)',
    panelBgStrong: 'rgba(255, 255, 255, 0.97)',
    textMain: '#1c151e',
    textMuted: '#6e6473',
    textSidebar: '#271d2b',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#1c151e',
    borderColor: 'rgba(102, 8, 116, 0.10)',
    inputBg: 'rgba(255, 255, 255, 0.95)',
    inputBorder: 'rgba(102, 8, 116, 0.12)',
    scrollbarThumb: 'rgba(102, 8, 116, 0.15)',
    sidebarHover: 'rgba(102, 8, 116, 0.05)',
    sidebarSurface: 'rgba(255, 255, 255, 0.84)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.72)',
    sidebarBorder: 'rgba(102, 8, 116, 0.12)',
    sidebarMuted: '#6e6473',
    sidebarDanger: '#b91c1c',
    sidebarDangerBg: 'rgba(185, 28, 28, 0.08)',
    composerMutedSurface: 'rgba(102, 8, 116, 0.04)',
    composerSelectedSurface: 'rgba(102, 8, 116, 0.08)',
    composerChipBorder: 'rgba(102, 8, 116, 0.14)',
    composerDangerText: '#b91c1c',
    composerDangerBorder: 'rgba(239, 68, 68, 0.28)',
    composerDangerBg: 'rgba(239, 68, 68, 0.08)',
    composerDangerFg: '#fca5a5',
    composerControlIcon: 'rgba(102, 8, 116, 0.48)',
    composerControlHoverBg: 'rgba(102, 8, 116, 0.08)',
    composerPillOpenShadow: '0 12px 26px rgba(102, 8, 116, 0.10)',
    composerSendBg: '#660874',
    composerSendFg: '#ffffff',
    composerSendDisabledBg: '#a38ca8',
    goatIconFrameBg: 'rgba(102, 8, 116, 0.08)',
    goatIconCircleBg: '#660874',
    codeInlineBg: 'rgba(102, 8, 116, 0.06)',
    codeBlockBg: '#18071b',
    tableHeaderBg: 'rgba(102, 8, 116, 0.06)',
    blockquoteBorder: 'rgba(102, 8, 116, 0.22)',
    linkColor: '#8e2f9d',
    assistantHover: 'rgba(102, 8, 116, 0.02)',
    previewCodeA: '#8e2f9d',
    previewCodeB: '#ceb272',
    previewDiffRemoved: '#fee4e2',
    previewDiffAdded: '#d1fadf',
    shadowColor: 'rgba(102, 8, 116, 0.12)',
  },
  dark: {
    mainBg: '#130c14',
    sidebarBg: '#100a11',
    chatBg: '#161018',
    userBubbleBg: '#481351',
    assistantBubbleBg: '#201622',
    panelBg: 'rgba(28, 21, 30, 0.84)',
    panelBgStrong: 'rgba(28, 21, 30, 0.96)',
    textMain: '#f7eff8',
    textMuted: '#a89db0',
    textSidebar: '#eee4f0',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#f7eff8',
    borderColor: 'rgba(255, 255, 255, 0.12)',
    inputBg: 'rgba(34, 25, 36, 0.94)',
    inputBorder: 'rgba(255, 255, 255, 0.12)',
    scrollbarThumb: 'rgba(255, 255, 255, 0.18)',
    sidebarHover: 'rgba(255, 255, 255, 0.06)',
    sidebarSurface: 'rgba(255, 255, 255, 0.10)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.08)',
    sidebarBorder: 'rgba(255, 255, 255, 0.12)',
    sidebarMuted: 'rgba(255, 255, 255, 0.55)',
    sidebarDanger: '#fca5a5',
    sidebarDangerBg: 'rgba(248, 113, 113, 0.12)',
    composerMutedSurface: 'rgba(255, 255, 255, 0.06)',
    composerSelectedSurface: 'rgba(255, 255, 255, 0.12)',
    composerChipBorder: 'rgba(255, 255, 255, 0.14)',
    composerDangerText: '#fca5a5',
    composerDangerBorder: 'rgba(248, 113, 113, 0.28)',
    composerDangerBg: 'rgba(248, 113, 113, 0.10)',
    composerDangerFg: '#fecaca',
    composerControlIcon: 'rgba(255, 255, 255, 0.55)',
    composerControlHoverBg: 'rgba(255, 255, 255, 0.12)',
    composerPillOpenShadow: '0 14px 34px rgba(0, 0, 0, 0.5)',
    composerSendBg: '#ceb272',
    composerSendFg: '#2a1e0b',
    composerSendDisabledBg: '#544658',
    goatIconFrameBg: 'rgba(255, 255, 255, 0.12)',
    goatIconCircleBg: '#481351',
    codeInlineBg: 'rgba(255, 255, 255, 0.12)',
    codeBlockBg: '#0d080f',
    tableHeaderBg: 'rgba(255, 255, 255, 0.08)',
    blockquoteBorder: 'rgba(255, 255, 255, 0.20)',
    linkColor: '#d2b980',
    assistantHover: 'rgba(255, 255, 255, 0.04)',
    previewCodeA: '#d2b980',
    previewCodeB: '#d581e2',
    previewDiffRemoved: '#4e282b',
    previewDiffAdded: '#223d2d',
    shadowColor: 'rgba(0, 0, 0, 0.5)',
  },
})

export const UI_FONT_OPTIONS: FontOption<UIFontId>[] = [
  {
    id: 'inter',
    label: 'Codex Sans',
    cssValue:
      '"Inter", "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif',
  },
  {
    id: 'system-sans',
    label: 'System UI',
    cssValue:
      'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif',
  },
  {
    id: 'humanist',
    label: 'Editorial Sans',
    cssValue:
      '"Segoe UI", "Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei UI", sans-serif',
  },
]

export const CODE_FONT_OPTIONS: FontOption<CodeFontId>[] = [
  {
    id: 'jetbrains',
    label: 'JetBrains Mono',
    cssValue: '"JetBrains Mono", "Fira Code", Consolas, monospace',
  },
  {
    id: 'sfmono',
    label: 'SF Mono Stack',
    cssValue: 'ui-monospace, "SFMono-Regular", "SF Mono", Consolas, monospace',
  },
  {
    id: 'mono',
    label: 'System Mono',
    cssValue: 'ui-monospace, "Cascadia Mono", "Liberation Mono", monospace',
  },
]

export const THEME_STYLES: ThemeStyleDefinition[] = [
  {
    id: 'classic',
    label: 'Classic',
    description: 'Clean neutral GOAT baseline with Codex-like density.',
    accentPresets: ['#2563eb', '#339cff', '#0ea5e9', '#14b8a6'],
    tokens: buildClassicTokens(),
  },
  {
    id: 'urochester',
    label: 'URochester',
    description: 'Classic URochester Navy and Dandelion Yellow, capturing the spirit of Meliora.',
    accentPresets: ['#001e5f', '#ffd82b', '#003eff', '#021bc3'],
    tokens: buildRochesterTokens(),
  },
  {
    id: 'thu',
    label: 'THU',
    description: 'Deep Tsinghua Purple and classic gold, representing elegance and academic rigor.',
    accentPresets: ['#660874', '#ceb272', '#8e2f9d', '#e0c78d'],
    tokens: buildThuTokens(),
  },
]

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
    .match(/^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([0-9.]+)\s*)?\)$/i)
  if (!rgbaMatch) return null

  const r = Number.parseInt(rgbaMatch[1] ?? '', 10)
  const g = Number.parseInt(rgbaMatch[2] ?? '', 10)
  const b = Number.parseInt(rgbaMatch[3] ?? '', 10)
  if ([r, g, b].some(channel => Number.isNaN(channel) || channel < 0 || channel > 255)) return null

  const hex = `#${[r, g, b].map(channel => channel.toString(16).padStart(2, '0')).join('')}`.toUpperCase()
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

export function loadStoredAppearance(storage: Pick<Storage, 'getItem' | 'removeItem'>): AppearanceConfig {
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
  const match = rgbaValue.match(/rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)/i)
  return match ? Number.parseFloat(match[1] ?? `${fallback}`) : fallback
}

export function getComputedThemeTokens(
  config: AppearanceConfig,
  prefersDark: boolean,
): ThemeTokenSet {
  const resolvedMode = resolveThemeMode(config.themeMode, prefersDark)
  const styleTokens = getThemeStyleDefinition(config.themeStyle).tokens[resolvedMode]
  const contrast = clampContrast(config.contrast)

  const borderBase = extractFirstAlpha(styleTokens.borderColor, resolvedMode === 'dark' ? 0.09 : 0.08)
  const inputBorderBase = extractFirstAlpha(styleTokens.inputBorder, resolvedMode === 'dark' ? 0.09 : 0.08)
  const sidebarBorderBase = extractFirstAlpha(styleTokens.sidebarBorder, resolvedMode === 'dark' ? 0.11 : 0.08)
  const sidebarSurfaceBase = extractFirstAlpha(styleTokens.sidebarSurface, resolvedMode === 'dark' ? 0.08 : 0.86)
  const sidebarSurfaceMutedBase = extractFirstAlpha(
    styleTokens.sidebarSurfaceMuted,
    resolvedMode === 'dark' ? 0.06 : 0.72,
  )

  const accent = normalizeHexColor(config.accentColor, DEFAULT_APPEARANCE_CONFIG.accentColor)
  const accentStrong = resolvedMode === 'dark' ? colorMix(accent, '#ffffff', 0.16) : colorMix(accent, '#0f172a', 0.12)
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
    sidebarSurface:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, sidebarAlpha)
        : rgba(255, 255, 255, sidebarAlpha),
    sidebarSurfaceMuted:
      resolvedMode === 'dark'
        ? rgba(255, 255, 255, sidebarMutedAlpha)
        : rgba(255, 255, 255, sidebarMutedAlpha),
    textMuted: resolvedMode === 'dark' ? colorMix(styleTokens.textMuted, '#ffffff', contrast / 500) : colorMix(styleTokens.textMuted, '#111827', contrast / 520),
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
      resolvedMode === 'dark' ? colorMix(accent, '#4b5563', 0.65) : colorMix(accent, '#cbd5e1', 0.62),
    linkColor: accentStrong,
    tableHeaderBg: accentSofter,
    codeInlineBg: resolvedMode === 'dark' ? accentSofter : rgba(...parseRgb(accent), 0.10),
    previewCodeA: accentStrong,
    previewCodeB: resolvedMode === 'dark' ? colorMix(accent, '#f8fafc', 0.34) : colorMix(accent, '#92400e', 0.28),
    previewDiffAdded: resolvedMode === 'dark' ? rgba(34, 197, 94, 0.22) : '#dff1e3',
    previewDiffRemoved: resolvedMode === 'dark' ? rgba(239, 68, 68, 0.22) : '#f8dfdb',
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
  root.style.setProperty('--theme-accent-soft', rgba(accentRgb[0], accentRgb[1], accentRgb[2], resolvedMode === 'dark' ? 0.22 : 0.14))
  root.style.setProperty('--theme-accent-contrast', getAccentForeground(config.accentColor))
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
    ['--composer-surface', `linear-gradient(180deg, ${tokens.panelBgStrong} 0%, ${tokens.panelBg} 100%)`],
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
  return `${getThemeStyleLabel(config.themeStyle)} · ${modeLabel}`
}

export function getStyleAccentPresets(styleId: AppearanceStyleId): string[] {
  return getThemeStyleDefinition(styleId).accentPresets
}
