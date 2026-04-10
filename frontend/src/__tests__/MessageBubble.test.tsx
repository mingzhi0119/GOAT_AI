import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MessageBubble from '../components/MessageBubble'
import { brandingConfig } from '../config/branding'

describe('MessageBubble', () => {
  it('renders visible user message content', () => {
    render(
      <MessageBubble message={{ id: 'm1', role: 'user', content: 'Hello from user' }} />,
    )
    expect(screen.getByText('Hello from user')).toBeInTheDocument()
    expect(screen.queryByLabelText(brandingConfig.displayName)).not.toBeInTheDocument()
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

  it('does not render assistant markdown chrome labels for assistant messages', () => {
    render(
      <MessageBubble
        message={{
          id: 'm3',
          role: 'assistant',
          content: 'Revenue mix looks stable.',
        }}
      />,
    )

    expect(screen.queryByText('Assistant')).not.toBeInTheDocument()
    expect(screen.queryByText('Markdown')).not.toBeInTheDocument()
    expect(screen.getByText('Revenue mix looks stable.')).toBeInTheDocument()
  })

  it('renders explicit LaTeX formulas when the message is complete', () => {
    const { container } = render(
      <MessageBubble
        message={{
          id: 'm4',
          role: 'assistant',
          createdAt: '2026-04-10T14:22:00Z',
          content: 'Energy is conserved.\n\n$$\nE=mc^2\n$$\n',
        }}
      />,
    )

    expect(container.querySelector('.katex-display')).toBeInTheDocument()
    expect(container.querySelectorAll('.katex').length).toBeGreaterThan(0)
    expect(container.textContent).not.toContain('$$')
    expect(screen.getByText('04:10')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy message' })).toBeInTheDocument()
  })

  it('keeps incomplete math as plain text while streaming', () => {
    const { container } = render(
      <MessageBubble
        message={{
          id: 'm5',
          role: 'assistant',
          createdAt: '2026-04-10T14:22:00Z',
          content: 'Energy is $$E=mc^2',
          isStreaming: true,
        }}
      />,
    )

    expect(container.querySelector('.katex')).not.toBeInTheDocument()
    expect(screen.getByText('Energy is $$E=mc^2')).toBeInTheDocument()
  })

  it('hides the thinking disclosure when the message is not marked to show thinking', () => {
    render(
      <MessageBubble
        message={{
          id: 'm6',
          role: 'assistant',
          createdAt: '2026-04-10T14:22:00Z',
          content: 'Final answer.',
          thinkingContent: 'Hidden reasoning trace',
          showThinking: false,
        }}
      />,
    )

    expect(screen.getByText('Final answer.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Thinking')).not.toBeInTheDocument()
    expect(screen.queryByText('Hidden reasoning trace')).not.toBeInTheDocument()
  })
})
