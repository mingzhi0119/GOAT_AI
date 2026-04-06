import { describe, expect, it, vi } from 'vitest'
import type { Message } from '../api/types'
import { buildMarkdownForExport, downloadChatAsMarkdown } from '../utils/exportChatMarkdown'

describe('exportChatMarkdown', () => {
  it('alerts when there are no exportable messages', () => {
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
    downloadChatAsMarkdown([], null)
    expect(alert).toHaveBeenCalledWith('No messages to export.')
    alert.mockRestore()
  })

  it('buildMarkdownForExport includes title and role headings', () => {
    const messages: Message[] = [
      { id: '1', role: 'user', content: 'Question' },
      { id: '2', role: 'assistant', content: 'Answer' },
    ]
    const md = buildMarkdownForExport(messages, 'Session A')
    expect(md).toContain('# Session A')
    expect(md).toContain('## User')
    expect(md).toContain('Question')
    expect(md).toContain('## Assistant')
    expect(md).toContain('Answer')
  })
})
