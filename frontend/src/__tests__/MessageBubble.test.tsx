import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MessageBubble from '../components/MessageBubble'

describe('MessageBubble', () => {
  it('renders visible user message content', () => {
    render(
      <MessageBubble message={{ id: 'm1', role: 'user', content: 'Hello from user' }} />,
    )
    expect(screen.getByText('Hello from user')).toBeInTheDocument()
  })

  it('renders artifact download card and resolves matching markdown links', () => {
    render(
      <MessageBubble
        message={{
          id: 'm2',
          role: 'assistant',
          content: '[brief.md](brief.md)',
          artifacts: [
            {
              artifact_id: 'art-1',
              filename: 'brief.md',
              mime_type: 'text/markdown',
              byte_size: 128,
              download_url: '/api/artifacts/art-1',
            },
          ],
        }}
      />,
    )
    const link = screen.getAllByRole('link', { name: /brief\.md/i })[0]
    expect(link).toHaveAttribute('href', '/api/artifacts/art-1')
    expect(screen.getByText('128 B')).toBeInTheDocument()
  })
})
