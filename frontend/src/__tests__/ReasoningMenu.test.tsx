import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import ReasoningMenu from '../components/ReasoningMenu'

describe('ReasoningMenu', () => {
  it('renders reasoning options and calls back with the selected level', async () => {
    const onSelectReasoningLevel = vi.fn()
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLButtonElement>()

    render(
      <>
        <button ref={triggerRef} id="reasoning-trigger" type="button">
          Reasoning
        </button>
        <ReasoningMenu
          isOpen={true}
          isNarrow={false}
          menuId="reasoning-menu"
          triggerRef={triggerRef}
          focusStrategy="selected"
          reasoningLevel="medium"
          onClose={onClose}
          onSelectReasoningLevel={onSelectReasoningLevel}
        />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByRole('menuitemradio', { name: 'Medium' })).toHaveFocus()
    })
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'High' }))
    expect(onSelectReasoningLevel).toHaveBeenCalledWith('high')
    expect(onClose).toHaveBeenCalled()
  })

  it('renders nothing when closed', () => {
    const { container } = render(
      <ReasoningMenu
        isOpen={false}
        isNarrow={false}
        menuId="reasoning-menu"
        focusStrategy="selected"
        reasoningLevel="low"
        onClose={vi.fn()}
        onSelectReasoningLevel={vi.fn()}
      />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it('supports arrow navigation and Escape focus return', async () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLButtonElement>()

    render(
      <>
        <button ref={triggerRef} id="reasoning-trigger" type="button">
          Reasoning
        </button>
        <ReasoningMenu
          isOpen={true}
          isNarrow={false}
          menuId="reasoning-menu"
          triggerRef={triggerRef}
          focusStrategy="selected"
          reasoningLevel="medium"
          onClose={onClose}
          onSelectReasoningLevel={vi.fn()}
        />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByRole('menuitemradio', { name: 'Medium' })).toHaveFocus()
    })

    fireEvent.keyDown(screen.getByRole('menu', { name: /reasoning menu/i }), { key: 'ArrowUp' })
    expect(screen.getByRole('menuitemradio', { name: 'Low' })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /reasoning menu/i }), { key: 'End' })
    expect(screen.getByRole('menuitemradio', { name: 'High' })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /reasoning menu/i }), { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
    await waitFor(() => {
      expect(triggerRef.current).toHaveFocus()
    })
  })
})
