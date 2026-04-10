import { describe, expect, it } from 'vitest'
import {
  APPEARANCE_STORAGE_KEY,
  DEFAULT_APPEARANCE_CONFIG,
  applyAppearanceToRoot,
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
})
