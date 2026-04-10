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
    mainBg: '#f3f5f8',
    sidebarBg: '#eef2f6',
    chatBg: '#f8fafc',
    userBubbleBg: '#17181c',
    assistantBubbleBg: '#ffffff',
    panelBg: 'rgba(255, 255, 255, 0.88)',
    panelBgStrong: 'rgba(255, 255, 255, 0.97)',
    textMain: '#16181d',
    textMuted: '#6f7683',
    textSidebar: '#1d2128',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#16181d',
    borderColor: 'rgba(18, 24, 38, 0.08)',
    inputBg: 'rgba(255, 255, 255, 0.94)',
    inputBorder: 'rgba(18, 24, 38, 0.08)',
    scrollbarThumb: '#cfd6df',
    sidebarHover: 'rgba(18, 24, 38, 0.045)',
    sidebarSurface: 'rgba(255, 255, 255, 0.86)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.72)',
    sidebarBorder: 'rgba(18, 24, 38, 0.08)',
    sidebarMuted: '#6b7280',
    sidebarDanger: '#b91c1c',
    sidebarDangerBg: 'rgba(185, 28, 28, 0.08)',
    composerMutedSurface: 'rgba(15, 23, 42, 0.03)',
    composerSelectedSurface: 'rgba(15, 23, 42, 0.085)',
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
    assistantHover: 'rgba(17, 24, 39, 0.028)',
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
    mainBg: '#f7f5f0',
    sidebarBg: '#f0ebe2',
    chatBg: '#faf7f1',
    userBubbleBg: '#1f2430',
    assistantBubbleBg: '#fffdf9',
    panelBg: 'rgba(255, 251, 243, 0.88)',
    panelBgStrong: 'rgba(255, 251, 243, 0.97)',
    textMain: '#1d1b18',
    textMuted: '#73695d',
    textSidebar: '#221f1a',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#1d1b18',
    borderColor: 'rgba(51, 41, 28, 0.10)',
    inputBg: 'rgba(255, 252, 247, 0.94)',
    inputBorder: 'rgba(51, 41, 28, 0.10)',
    scrollbarThumb: '#d8cbbb',
    sidebarHover: 'rgba(61, 44, 20, 0.06)',
    sidebarSurface: 'rgba(255, 251, 243, 0.84)',
    sidebarSurfaceMuted: 'rgba(255, 251, 243, 0.72)',
    sidebarBorder: 'rgba(61, 44, 20, 0.10)',
    sidebarMuted: '#776b58',
    sidebarDanger: '#b91c1c',
    sidebarDangerBg: 'rgba(185, 28, 28, 0.08)',
    composerMutedSurface: 'rgba(86, 64, 34, 0.05)',
    composerSelectedSurface: 'rgba(86, 64, 34, 0.10)',
    composerChipBorder: 'rgba(51, 41, 28, 0.14)',
    composerDangerText: '#b91c1c',
    composerDangerBorder: 'rgba(239, 68, 68, 0.28)',
    composerDangerBg: 'rgba(239, 68, 68, 0.08)',
    composerDangerFg: '#fca5a5',
    composerControlIcon: 'rgba(34, 28, 20, 0.48)',
    composerControlHoverBg: 'rgba(61, 44, 20, 0.08)',
    composerPillOpenShadow: '0 12px 26px rgba(50, 35, 17, 0.12)',
    composerSendBg: '#312114',
    composerSendFg: '#fff9f0',
    composerSendDisabledBg: '#b6a48d',
    goatIconFrameBg: 'rgba(49, 33, 20, 0.08)',
    goatIconCircleBg: '#2f241b',
    codeInlineBg: 'rgba(86, 64, 34, 0.08)',
    codeBlockBg: '#171514',
    tableHeaderBg: 'rgba(86, 64, 34, 0.06)',
    blockquoteBorder: 'rgba(51, 41, 28, 0.20)',
    linkColor: '#8b2e17',
    assistantHover: 'rgba(61, 44, 20, 0.03)',
    previewCodeA: '#7c2d12',
    previewCodeB: '#92400e',
    previewDiffRemoved: '#f2d7cc',
    previewDiffAdded: '#dfe9d8',
    shadowColor: 'rgba(50, 35, 17, 0.14)',
  },
  dark: {
    mainBg: '#131111',
    sidebarBg: '#16110d',
    chatBg: '#1a1512',
    userBubbleBg: '#3f2a1d',
    assistantBubbleBg: '#221b16',
    panelBg: 'rgba(33, 25, 21, 0.84)',
    panelBgStrong: 'rgba(33, 25, 21, 0.96)',
    textMain: '#f6f0e9',
    textMuted: '#c4b7a7',
    textSidebar: '#fff5e9',
    textUserBubble: '#fff8f2',
    textAssistantBubble: '#f6f0e9',
    borderColor: 'rgba(255, 232, 208, 0.11)',
    inputBg: 'rgba(31, 24, 20, 0.94)',
    inputBorder: 'rgba(255, 232, 208, 0.11)',
    scrollbarThumb: '#584639',
    sidebarHover: 'rgba(255, 237, 218, 0.07)',
    sidebarSurface: 'rgba(255, 246, 235, 0.09)',
    sidebarSurfaceMuted: 'rgba(255, 246, 235, 0.07)',
    sidebarBorder: 'rgba(255, 237, 218, 0.12)',
    sidebarMuted: 'rgba(255, 245, 233, 0.58)',
    sidebarDanger: '#fda4af',
    sidebarDangerBg: 'rgba(253, 164, 175, 0.14)',
    composerMutedSurface: 'rgba(255, 246, 235, 0.06)',
    composerSelectedSurface: 'rgba(255, 246, 235, 0.12)',
    composerChipBorder: 'rgba(255, 246, 235, 0.14)',
    composerDangerText: '#fda4af',
    composerDangerBorder: 'rgba(253, 164, 175, 0.26)',
    composerDangerBg: 'rgba(253, 164, 175, 0.10)',
    composerDangerFg: '#fecdd3',
    composerControlIcon: 'rgba(255, 244, 232, 0.6)',
    composerControlHoverBg: 'rgba(255, 246, 235, 0.10)',
    composerPillOpenShadow: '0 14px 34px rgba(0, 0, 0, 0.48)',
    composerSendBg: '#f1d6b8',
    composerSendFg: '#24160d',
    composerSendDisabledBg: '#6a574b',
    goatIconFrameBg: 'rgba(255, 244, 232, 0.12)',
    goatIconCircleBg: '#563626',
    codeInlineBg: 'rgba(255, 246, 235, 0.12)',
    codeBlockBg: '#0f0b08',
    tableHeaderBg: 'rgba(255, 246, 235, 0.06)',
    blockquoteBorder: 'rgba(255, 246, 235, 0.20)',
    linkColor: '#f6b062',
    assistantHover: 'rgba(255, 246, 235, 0.04)',
    previewCodeA: '#fbbf24',
    previewCodeB: '#fb7185',
    previewDiffRemoved: '#562d2e',
    previewDiffAdded: '#243a2d',
    shadowColor: 'rgba(0, 0, 0, 0.48)',
  },
})

const buildThuTokens = (): Record<ResolvedThemeMode, ThemeTokenSet> => ({
  light: {
    mainBg: '#f4f6f5',
    sidebarBg: '#e9edeb',
    chatBg: '#f7faf8',
    userBubbleBg: '#12261f',
    assistantBubbleBg: '#ffffff',
    panelBg: 'rgba(250, 253, 251, 0.88)',
    panelBgStrong: 'rgba(250, 253, 251, 0.97)',
    textMain: '#16211d',
    textMuted: '#64736d',
    textSidebar: '#17211d',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#16211d',
    borderColor: 'rgba(21, 43, 35, 0.09)',
    inputBg: 'rgba(255, 255, 255, 0.95)',
    inputBorder: 'rgba(21, 43, 35, 0.09)',
    scrollbarThumb: '#c5d2cc',
    sidebarHover: 'rgba(21, 43, 35, 0.05)',
    sidebarSurface: 'rgba(255, 255, 255, 0.84)',
    sidebarSurfaceMuted: 'rgba(255, 255, 255, 0.72)',
    sidebarBorder: 'rgba(21, 43, 35, 0.09)',
    sidebarMuted: '#63706b',
    sidebarDanger: '#b91c1c',
    sidebarDangerBg: 'rgba(185, 28, 28, 0.08)',
    composerMutedSurface: 'rgba(10, 54, 37, 0.04)',
    composerSelectedSurface: 'rgba(10, 54, 37, 0.10)',
    composerChipBorder: 'rgba(21, 43, 35, 0.12)',
    composerDangerText: '#b91c1c',
    composerDangerBorder: 'rgba(239, 68, 68, 0.28)',
    composerDangerBg: 'rgba(239, 68, 68, 0.08)',
    composerDangerFg: '#fca5a5',
    composerControlIcon: 'rgba(18, 38, 31, 0.46)',
    composerControlHoverBg: 'rgba(10, 54, 37, 0.08)',
    composerPillOpenShadow: '0 12px 26px rgba(10, 37, 29, 0.12)',
    composerSendBg: '#17392f',
    composerSendFg: '#f4fbf8',
    composerSendDisabledBg: '#8da69d',
    goatIconFrameBg: 'rgba(23, 57, 47, 0.08)',
    goatIconCircleBg: '#1f4035',
    codeInlineBg: 'rgba(10, 54, 37, 0.08)',
    codeBlockBg: '#081510',
    tableHeaderBg: 'rgba(10, 54, 37, 0.06)',
    blockquoteBorder: 'rgba(21, 43, 35, 0.20)',
    linkColor: '#0f766e',
    assistantHover: 'rgba(21, 43, 35, 0.028)',
    previewCodeA: '#0f766e',
    previewCodeB: '#ea580c',
    previewDiffRemoved: '#f2ddd6',
    previewDiffAdded: '#d8e9df',
    shadowColor: 'rgba(10, 37, 29, 0.12)',
  },
  dark: {
    mainBg: '#081411',
    sidebarBg: '#09100d',
    chatBg: '#0d1915',
    userBubbleBg: '#18352c',
    assistantBubbleBg: '#12211c',
    panelBg: 'rgba(13, 25, 21, 0.84)',
    panelBgStrong: 'rgba(13, 25, 21, 0.96)',
    textMain: '#edf8f3',
    textMuted: '#9eb6ad',
    textSidebar: '#eef8f4',
    textUserBubble: '#ffffff',
    textAssistantBubble: '#edf8f3',
    borderColor: 'rgba(227, 247, 238, 0.09)',
    inputBg: 'rgba(16, 31, 26, 0.94)',
    inputBorder: 'rgba(227, 247, 238, 0.09)',
    scrollbarThumb: '#36524a',
    sidebarHover: 'rgba(227, 247, 238, 0.055)',
    sidebarSurface: 'rgba(227, 247, 238, 0.08)',
    sidebarSurfaceMuted: 'rgba(227, 247, 238, 0.06)',
    sidebarBorder: 'rgba(227, 247, 238, 0.10)',
    sidebarMuted: 'rgba(227, 247, 238, 0.56)',
    sidebarDanger: '#fca5a5',
    sidebarDangerBg: 'rgba(248, 113, 113, 0.12)',
    composerMutedSurface: 'rgba(227, 247, 238, 0.05)',
    composerSelectedSurface: 'rgba(227, 247, 238, 0.11)',
    composerChipBorder: 'rgba(227, 247, 238, 0.14)',
    composerDangerText: '#fca5a5',
    composerDangerBorder: 'rgba(248, 113, 113, 0.28)',
    composerDangerBg: 'rgba(248, 113, 113, 0.10)',
    composerDangerFg: '#fecaca',
    composerControlIcon: 'rgba(237, 248, 243, 0.58)',
    composerControlHoverBg: 'rgba(227, 247, 238, 0.10)',
    composerPillOpenShadow: '0 14px 34px rgba(0, 0, 0, 0.48)',
    composerSendBg: '#ddf4eb',
    composerSendFg: '#10211c',
    composerSendDisabledBg: '#4e6a62',
    goatIconFrameBg: 'rgba(227, 247, 238, 0.12)',
    goatIconCircleBg: '#21473b',
    codeInlineBg: 'rgba(227, 247, 238, 0.12)',
    codeBlockBg: '#06100d',
    tableHeaderBg: 'rgba(227, 247, 238, 0.05)',
    blockquoteBorder: 'rgba(227, 247, 238, 0.20)',
    linkColor: '#5eead4',
    assistantHover: 'rgba(227, 247, 238, 0.04)',
    previewCodeA: '#5eead4',
    previewCodeB: '#fb923c',
    previewDiffRemoved: '#4e2e2d',
    previewDiffAdded: '#21392d',
    shadowColor: 'rgba(0, 0, 0, 0.48)',
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
    accentPresets: ['#339cff', '#2563eb', '#0ea5e9', '#14b8a6'],
    tokens: buildClassicTokens(),
  },
  {
    id: 'urochester',
    label: 'URochester',
    description: 'Warm ivory surfaces with a restrained Rochester palette.',
    accentPresets: ['#9f4b1b', '#c27d18', '#7c2d12', '#8b5cf6'],
    tokens: buildRochesterTokens(),
  },
  {
    id: 'thu',
    label: 'THU',
    description: 'Calm jade greens with dark, polished utility surfaces.',
    accentPresets: ['#0f766e', '#0f9f8f', '#15803d', '#ea580c'],
    tokens: buildThuTokens(),
  },
]

export const DEFAULT_APPEARANCE_CONFIG: AppearanceConfig = {
  themeMode: 'system',
  themeStyle: 'classic',
  accentColor: '#339cff',
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

function parseRgb(value: string): [number, number, number] {
  const normalized = value.replace('#', '')
  const r = Number.parseInt(normalized.slice(0, 2), 16)
  const g = Number.parseInt(normalized.slice(2, 4), 16)
  const b = Number.parseInt(normalized.slice(4, 6), 16)
  return [r, g, b]
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

  const sidebarAlpha = config.translucentSidebar
    ? Math.max(0.48, sidebarSurfaceBase)
    : Math.min(1, sidebarSurfaceBase + 0.12)
  const sidebarMutedAlpha = config.translucentSidebar
    ? Math.max(0.38, sidebarSurfaceMutedBase)
    : Math.min(1, sidebarSurfaceMutedBase + 0.14)

  return {
    ...styleTokens,
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
    composerSendFg: getAccentForeground(accent),
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
