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

  it('keeps the active badge anchored without displacing the theme title', () => {
    render(
      <AppearancePanel
        open={true}
        appearance={{ ...DEFAULT_APPEARANCE_CONFIG, themeStyle: 'thu' }}
        effectiveMode="light"
        onClose={vi.fn()}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    const activeBadge = screen.getByText('Active')
    expect(activeBadge).toHaveClass('absolute', 'right-0', 'top-0')
    expect(screen.getByText('THU')).toBeInTheDocument()
  })

  it('renders the contrast slider with a dedicated draggable class', () => {
    render(
      <AppearancePanel
        open={true}
        appearance={DEFAULT_APPEARANCE_CONFIG}
        effectiveMode="light"
        onClose={vi.fn()}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    expect(screen.getByLabelText(/contrast/i)).toHaveClass('appearance-contrast-slider')
  })
})
