/* @vitest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it } from 'vitest'
import {
  APPEARANCE_STORAGE_KEY,
  AppearanceProvider,
  useAppearance,
} from '../hooks/useAppearance'

function wrapper({ children }: PropsWithChildren) {
  return <AppearanceProvider>{children}</AppearanceProvider>
}

describe('useAppearance', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme-style')
    document.documentElement.removeAttribute('data-theme-resolved')
  })

  it('hydrates from storage and applies appearance tokens to the root element', async () => {
    localStorage.setItem(
      APPEARANCE_STORAGE_KEY,
      JSON.stringify({
        themeMode: 'dark',
        themeStyle: 'thu',
        accentColor: '#0088cc',
        uiFont: 'humanist',
        codeFont: 'mono',
        contrast: 68,
        translucentSidebar: false,
      }),
    )

    const { result } = renderHook(() => useAppearance(), { wrapper })

    await waitFor(() => expect(result.current.appearance.themeStyle).toBe('thu'))
    expect(document.documentElement.dataset.themeStyle).toBe('thu')
    expect(document.documentElement.dataset.themeResolved).toBe('dark')
    expect(document.documentElement.style.getPropertyValue('--theme-accent')).toBe('#0088cc')
  })

  it('updates and resets appearance state while persisting to storage', async () => {
    const { result } = renderHook(() => useAppearance(), { wrapper })

    act(() => {
      result.current.updateAppearance({
        themeMode: 'light',
        themeStyle: 'urochester',
        accentColor: '#112233',
        contrast: 72,
      })
    })

    await waitFor(() => expect(result.current.appearance.themeStyle).toBe('urochester'))
    expect(localStorage.getItem(APPEARANCE_STORAGE_KEY)).toContain('"themeStyle":"urochester"')

    act(() => {
      result.current.resetAppearance()
    })

    expect(result.current.appearance.themeStyle).toBe('classic')
    expect(result.current.appearance.themeMode).toBe('system')
  })
})
