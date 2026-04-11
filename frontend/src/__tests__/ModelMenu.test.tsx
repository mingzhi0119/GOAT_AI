import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ModelMenu from '../components/ModelMenu'

describe('ModelMenu', () => {
  it('renders model choices and calls back when one is selected', () => {
    const onSelectModel = vi.fn()

    render(
      <ModelMenu
        isOpen={true}
        isNarrow={false}
        models={['gemma4:26b', 'qwen2.5:14b']}
        selectedModel="gemma4:26b"
        onSelectModel={onSelectModel}
      />,
    )

    expect(screen.getByRole('menu', { name: /model menu/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('menuitemradio', { name: /qwen2.5:14b/i }))
    expect(onSelectModel).toHaveBeenCalledWith('qwen2.5:14b')
  })

  it('renders nothing when closed', () => {
    const { container } = render(
      <ModelMenu
        isOpen={false}
        isNarrow={false}
        models={['gemma4:26b']}
        selectedModel="gemma4:26b"
        onSelectModel={vi.fn()}
      />,
    )

    expect(container).toBeEmptyDOMElement()
  })
})
