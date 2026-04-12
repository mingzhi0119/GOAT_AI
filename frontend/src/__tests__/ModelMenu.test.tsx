import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import ModelMenu from '../components/ModelMenu'

describe('ModelMenu', () => {
  it('renders model choices and calls back when one is selected', async () => {
    const onSelectModel = vi.fn()
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLButtonElement>()

    render(
      <>
        <button ref={triggerRef} id="model-trigger" type="button">
          Model
        </button>
        <ModelMenu
          isOpen={true}
          isNarrow={false}
          menuId="model-menu"
          triggerRef={triggerRef}
          focusStrategy="selected"
          models={['gemma4:26b', 'qwen2.5:14b']}
          selectedModel="gemma4:26b"
          onClose={onClose}
          onSelectModel={onSelectModel}
        />
      </>,
    )

    expect(screen.getByRole('menu', { name: /model menu/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('menuitemradio', { name: /gemma4:26b/i })).toHaveFocus()
    })
    fireEvent.click(screen.getByRole('menuitemradio', { name: /qwen2.5:14b/i }))
    expect(onSelectModel).toHaveBeenCalledWith('qwen2.5:14b')
    expect(onClose).toHaveBeenCalled()
  })

  it('renders nothing when closed', () => {
    const { container } = render(
      <ModelMenu
        isOpen={false}
        isNarrow={false}
        menuId="model-menu"
        focusStrategy="selected"
        models={['gemma4:26b']}
        selectedModel="gemma4:26b"
        onClose={vi.fn()}
        onSelectModel={vi.fn()}
      />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it('supports arrow navigation, Home/End, and Escape focus return', async () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLButtonElement>()

    render(
      <>
        <button ref={triggerRef} id="model-trigger" type="button">
          Model
        </button>
        <ModelMenu
          isOpen={true}
          isNarrow={false}
          menuId="model-menu"
          triggerRef={triggerRef}
          focusStrategy="selected"
          models={['gemma4:26b', 'qwen2.5:14b', 'llama3.2:8b']}
          selectedModel="qwen2.5:14b"
          onClose={onClose}
          onSelectModel={vi.fn()}
        />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByRole('menuitemradio', { name: /qwen2.5:14b/i })).toHaveFocus()
    })

    fireEvent.keyDown(screen.getByRole('menu', { name: /model menu/i }), { key: 'ArrowDown' })
    expect(screen.getByRole('menuitemradio', { name: /llama3.2:8b/i })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /model menu/i }), { key: 'Home' })
    expect(screen.getByRole('menuitemradio', { name: /gemma4:26b/i })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /model menu/i }), { key: 'End' })
    expect(screen.getByRole('menuitemradio', { name: /llama3.2:8b/i })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /model menu/i }), { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
    await waitFor(() => {
      expect(triggerRef.current).toHaveFocus()
    })
  })
})
