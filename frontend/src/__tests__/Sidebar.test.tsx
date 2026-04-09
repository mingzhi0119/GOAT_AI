import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import Sidebar from '../components/Sidebar'

function renderSidebar() {
  return render(
    <Sidebar
      onClearChat={vi.fn()}
      userName="Mingzhi"
      onUserNameChange={vi.fn()}
      historySessions={[
        {
          id: 'session-1',
          title: 'Strategy review',
          model: 'gpt-5.4',
          created_at: '2026-04-09T12:00:00Z',
          updated_at: '2026-04-09T13:00:00Z',
        },
      ]}
      isLoadingHistory={false}
      historyError={null}
      onLoadHistorySession={vi.fn()}
      onDeleteHistorySession={vi.fn()}
      onRefreshHistory={vi.fn()}
      onDeleteAllHistory={vi.fn()}
    />,
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
})
