import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import MessageBubble from '../components/MessageBubble'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { brandingConfig } from '../config/branding'

describe('MessageBubble', () => {
  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

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

  it('downloads artifacts with stored protected-access headers', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')

    const fetchMock = vi.fn().mockResolvedValue(
      new Response('artifact body', {
        status: 200,
        headers: {
          'Content-Disposition': 'attachment; filename="brief.md"',
        },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const originalCreateObjectURL = URL.createObjectURL
    const originalRevokeObjectURL = URL.revokeObjectURL
    const createObjectURL = vi.fn(() => 'blob:artifact')
    const revokeObjectURL = vi.fn()
    Object.assign(URL, {
      createObjectURL,
      revokeObjectURL,
    })
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {})

    try {
      render(
        <MessageBubble
          message={{
            id: 'm2b',
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

      fireEvent.click(screen.getAllByRole('link', { name: /brief\.md/i })[0]!)

      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith('/api/artifacts/art-1', {
          method: 'GET',
          credentials: 'same-origin',
          headers: {
            'X-GOAT-API-Key': 'secret-123',
            'X-GOAT-Owner-Id': 'alice',
          },
        }),
      )
      expect(createObjectURL).toHaveBeenCalled()
      expect(clickSpy).toHaveBeenCalled()
    } finally {
      Object.assign(URL, {
        createObjectURL: originalCreateObjectURL,
        revokeObjectURL: originalRevokeObjectURL,
      })
    }
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
    expect(screen.getByRole('button', { name: 'Copy message' })).toBeInTheDocument()
    expect(screen.queryByText('04:10')).not.toBeInTheDocument()
    const footer = container.querySelector('.assistant-copy-footer')
    expect(footer).toHaveClass('min-h-6')
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
    expect(container.textContent).toContain('Energy is$$E=mc^2')
  })

  it('renders a closed formula immediately while leaving the next incomplete formula as plain text', () => {
    const { container } = render(
      <MessageBubble
        message={{
          id: 'm5b',
          role: 'assistant',
          createdAt: '2026-04-10T14:22:00Z',
          content: 'First $E=mc^2$ then $$x^2',
          isStreaming: true,
        }}
      />,
    )

    expect(container.querySelector('.katex')).toBeInTheDocument()
    expect(container.textContent).toContain('then$$x^2')
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

  it('keeps the assistant copy footer height stable on hover', () => {
    const { container } = render(
      <MessageBubble
        message={{
          id: 'm7',
          role: 'assistant',
          content: 'Hover should not move me.',
        }}
      />,
    )

    const footer = container.querySelector('.assistant-copy-footer')
    const card = container.querySelector('.assistant-document-card')
    expect(footer).toHaveClass('min-h-6')
    expect(footer?.className).not.toContain('h-0')

    fireEvent.mouseEnter(card!)
    expect(screen.getByRole('button', { name: 'Copy message' })).toBeInTheDocument()
    expect(screen.queryByText(/\d{2}:\d{2}/)).not.toBeInTheDocument()
  })
})
