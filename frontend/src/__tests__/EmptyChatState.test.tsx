import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EmptyChatState from '../components/EmptyChatState'
import { getChatLayoutDecisions } from '../utils/chatLayout'

describe('EmptyChatState', () => {
  it('shows the model name without a vision suffix and sends starter prompts', () => {
    const onSendMessage = vi.fn()

    render(
      <EmptyChatState
        starterPrompts={[
          { text: 'Prompt one', kind: 'base' },
          { text: 'Prompt two', kind: 'base' },
          { text: 'Prompt three', kind: 'suffix' },
          { text: 'Prompt four', kind: 'template' },
        ]}
        selectedModel="qwen3"
        layoutDecisions={getChatLayoutDecisions('wide')}
        onSendMessage={onSendMessage}
      />,
    )

    expect(screen.getByText('Model:')).toBeInTheDocument()
    expect(screen.getByText('qwen3')).toBeInTheDocument()
    expect(screen.queryByText(/^vision$/i)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /prompt three/i }))
    expect(onSendMessage).toHaveBeenCalledWith('Prompt three')
  })
})
