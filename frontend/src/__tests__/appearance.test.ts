import { describe, expect, it } from 'vitest'
import {
  APPEARANCE_STORAGE_KEY,
  DEFAULT_APPEARANCE_CONFIG,
  applyAppearanceToRoot,
  formatColorTokenDisplay,
  getComputedThemeTokens,
  loadStoredAppearance,
  sanitizeAppearanceConfig,
} from '../utils/appearance'

describe('appearance helpers', () => {
  it('sanitizes malformed config values back to safe defaults', () => {
    expect(
      sanitizeAppearanceConfig({
        themeMode: 'invalid',
        themeStyle: 'thu',
        accentColor: 'red',
        uiFont: 'unknown',
        codeFont: 'jetbrains',
        contrast: 240,
        translucentSidebar: 'yes',
      }),
    ).toEqual({
      ...DEFAULT_APPEARANCE_CONFIG,
      themeStyle: 'thu',
      codeFont: 'jetbrains',
      contrast: 100,
    })
  })

  it('loads and migrates the legacy binary theme key', () => {
    const storage = {
      getItem: (key: string) => {
        if (key === APPEARANCE_STORAGE_KEY) return null
        if (key === 'goat-ai-theme') return 'dark'
        return null
      },
      removeItem: () => undefined,
    }

    expect(loadStoredAppearance(storage)).toEqual({
      ...DEFAULT_APPEARANCE_CONFIG,
      themeMode: 'dark',
    })
  })

  it('uses blue as the classic default accent and applies it to classic user bubbles', () => {
    expect(DEFAULT_APPEARANCE_CONFIG.accentColor).toBe('#2563eb')

    const tokens = getComputedThemeTokens(DEFAULT_APPEARANCE_CONFIG, false)
    expect(tokens.userBubbleBg).toBe('#2563eb')
    expect(tokens.chatBg).toBe('#ffffff')
    expect(tokens.sidebarBg).toBe('#f4f4f5')
  })

  it('applies accent color to user bubbles across non-classic themes too', () => {
    const rochesterTokens = getComputedThemeTokens(
      { ...DEFAULT_APPEARANCE_CONFIG, themeStyle: 'urochester', accentColor: '#ffd82b' },
      false,
    )
    const thuTokens = getComputedThemeTokens(
      { ...DEFAULT_APPEARANCE_CONFIG, themeStyle: 'thu', accentColor: '#8e2f9d' },
      false,
    )

    expect(rochesterTokens.userBubbleBg).toBe('#ffd82b')
    expect(rochesterTokens.textUserBubble).toBe('#111827')
    expect(thuTokens.userBubbleBg).toBe('#8e2f9d')
    expect(thuTokens.textUserBubble).toBe('#ffffff')
  })

  it('applies attributes and semantic vars to the document root', () => {
    const root = document.documentElement
    applyAppearanceToRoot(
      root,
      {
        ...DEFAULT_APPEARANCE_CONFIG,
        themeMode: 'dark',
        themeStyle: 'urochester',
        accentColor: '#9f4b1b',
        contrast: 67,
        translucentSidebar: false,
      },
      true,
    )

    expect(root.dataset.themeMode).toBe('dark')
    expect(root.dataset.themeResolved).toBe('dark')
    expect(root.dataset.themeStyle).toBe('urochester')
    expect(root.dataset.sidebarTranslucent).toBe('false')
    expect(root.style.getPropertyValue('--theme-accent')).toBe('#9f4b1b')
    expect(root.style.getPropertyValue('--bg-main')).not.toBe('')
    expect(root.style.getPropertyValue('--composer-send-bg')).toBe('#9f4b1b')
  })

  it('formats appearance color readouts as hex with optional opacity', () => {
    expect(formatColorTokenDisplay('rgba(255, 255, 255, 0.97)')).toBe('#FFFFFF, 97%')
    expect(formatColorTokenDisplay('rgba(0, 30, 95, 0.08)')).toBe('#001E5F, 8%')
    expect(formatColorTokenDisplay('rgba(255, 255, 255, 1)')).toBe('#FFFFFF')
    expect(formatColorTokenDisplay('rgba(255, 255, 255, 0)')).toBe('#FFFFFF')
    expect(formatColorTokenDisplay('#021d59')).toBe('#021D59')
  })
})
