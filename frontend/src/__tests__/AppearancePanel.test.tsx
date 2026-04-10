import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AppearancePanel from '../components/AppearancePanel'
import { DEFAULT_APPEARANCE_CONFIG } from '../utils/appearance'

describe('AppearancePanel', () => {
  it('renders Codex-like controls and dispatches live updates', () => {
    const onChange = vi.fn()
    const onReset = vi.fn()
    const onClose = vi.fn()

    render(
      <AppearancePanel
        open={true}
        appearance={DEFAULT_APPEARANCE_CONFIG}
        effectiveMode="dark"
        onClose={onClose}
        onChange={onChange}
        onReset={onReset}
      />,
    )

    expect(screen.getByRole('dialog', { name: /appearance settings/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /system/i })).toHaveAttribute('aria-checked', 'true')

    fireEvent.click(screen.getByRole('radio', { name: /light/i }))
    fireEvent.change(screen.getByLabelText(/contrast/i), { target: { value: '72' } })
    fireEvent.click(screen.getByRole('switch', { name: /translucent sidebar/i }))
    fireEvent.click(screen.getByRole('button', { name: /reset defaults/i }))

    expect(onChange).toHaveBeenCalledWith({ themeMode: 'light' })
    expect(onChange).toHaveBeenCalledWith({ contrast: 72 })
    expect(onChange).toHaveBeenCalledWith({ translucentSidebar: false })
    expect(onReset).toHaveBeenCalled()
  })
})
