import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { HistorySessionItem } from '../api/history'
import Sidebar from '../components/Sidebar'

function buildProps(themeStyle: 'classic' | 'urochester' | 'thu' = 'classic') {
  const historySessions: HistorySessionItem[] = [
    {
      id: 'session-1',
      title: 'Strategy review',
      model: 'gpt-5.4',
      created_at: '2026-04-09T12:00:00Z',
      updated_at: '2026-04-09T13:00:00Z',
    },
  ]

  return {
    onClearChat: vi.fn(),
    userName: 'Mingzhi',
    onUserNameChange: vi.fn(),
    themeStyle,
    currentSessionId: null,
    historySessions,
    isLoadingHistory: false,
    historyError: null,
    onLoadHistorySession: vi.fn(),
    onDeleteHistorySession: vi.fn(),
    onRefreshHistory: vi.fn(),
    onDeleteAllHistory: vi.fn(),
  }
}

function renderSidebar(themeStyle: 'classic' | 'urochester' | 'thu' = 'classic') {
  return render(
    <Sidebar {...buildProps(themeStyle)} />,
  )
}

describe('Sidebar', () => {
  it('does not render the Your Name section', () => {
    renderSidebar()

    expect(screen.queryByText('Your Name')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/optional - ai will address you/i)).not.toBeInTheDocument()
  })

  it('renders history rows without timestamps', () => {
    renderSidebar()

    expect(screen.getByText('Strategy review')).toBeInTheDocument()
    expect(screen.queryByText(/2026/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/13:00/i)).not.toBeInTheDocument()
  })

  it('keeps delete buttons mounted but visually hidden by default', () => {
    renderSidebar()

    const deleteButton = screen.getByTitle('Delete conversation')
    expect(deleteButton).toBeInTheDocument()
    expect(deleteButton.className).toContain('opacity-0')
    expect(deleteButton.className).toContain('group-hover/history:opacity-100')
  })

  it('only marks the active history session with aria-current', () => {
    const historySessions: HistorySessionItem[] = [
      {
        id: 'session-1',
        title: 'Strategy review',
        model: 'gpt-5.4',
        created_at: '2026-04-09T12:00:00Z',
        updated_at: '2026-04-09T13:00:00Z',
      },
      {
        id: 'session-2',
        title: 'Other chat',
        model: 'gpt-5.4',
        created_at: '2026-04-09T14:00:00Z',
        updated_at: '2026-04-09T15:00:00Z',
      },
    ]

    render(
      <Sidebar
        {...buildProps('classic')}
        historySessions={historySessions}
        currentSessionId="session-1"
      />,
    )

    expect(screen.getByTitle('Strategy review')).toHaveAttribute('aria-current', 'true')
    expect(screen.getByTitle('Other chat')).not.toHaveAttribute('aria-current')
  })

  it('switches the footer school logo by theme style', () => {
    const { rerender } = renderSidebar('urochester')

    expect(
      screen.getByAltText('Simon Business School - University of Rochester'),
    ).toBeInTheDocument()

    rerender(<Sidebar {...buildProps('thu')} />)

    expect(screen.getByAltText('Tsinghua University')).toBeInTheDocument()
    expect(
      screen.queryByAltText('Simon Business School - University of Rochester'),
    ).not.toBeInTheDocument()
  })

  it('hides the school logo in classic theme', () => {
    renderSidebar('classic')

    expect(
      screen.queryByAltText('Simon Business School - University of Rochester'),
    ).not.toBeInTheDocument()
    expect(screen.queryByAltText('Tsinghua University')).not.toBeInTheDocument()
  })
})
