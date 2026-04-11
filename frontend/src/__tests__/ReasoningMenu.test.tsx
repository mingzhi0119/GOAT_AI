import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ReasoningMenu from '../components/ReasoningMenu'

describe('ReasoningMenu', () => {
  it('renders reasoning options and calls back with the selected level', () => {
    const onSelectReasoningLevel = vi.fn()

    render(
      <ReasoningMenu
        isOpen={true}
        isNarrow={false}
        reasoningLevel="medium"
        onSelectReasoningLevel={onSelectReasoningLevel}
      />,
    )

    fireEvent.click(screen.getByRole('menuitemradio', { name: 'High' }))
    expect(onSelectReasoningLevel).toHaveBeenCalledWith('high')
  })

  it('renders nothing when closed', () => {
    const { container } = render(
      <ReasoningMenu
        isOpen={false}
        isNarrow={false}
        reasoningLevel="low"
        onSelectReasoningLevel={vi.fn()}
      />,
    )

    expect(container).toBeEmptyDOMElement()
  })
})
