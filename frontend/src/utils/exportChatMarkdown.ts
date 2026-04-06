import type { Message } from '../api/types'

/** Build Markdown text from completed messages (unit-testable; no DOM). */
export function buildMarkdownForExport(messages: Message[], title?: string | null): string {
  const completed = messages.filter(m => !m.isStreaming && m.content.trim().length > 0)
  if (completed.length === 0) {
    return ''
  }
  const header = title?.trim() || 'GOAT AI conversation'
  const lines: string[] = [`# ${header}`, '']
  for (const m of completed) {
    const label = m.role === 'user' ? 'User' : 'Assistant'
    lines.push(`## ${label}`, '', m.content.trim(), '')
  }
  return lines.join('\n')
}

/** Build a Markdown document from chat messages and trigger download. */
export function downloadChatAsMarkdown(messages: Message[], title?: string | null): void {
  const body = buildMarkdownForExport(messages, title)
  if (!body) {
    window.alert('No messages to export.')
    return
  }
  const blob = new Blob([body], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  const a = document.createElement('a')
  a.href = url
  a.download = `goat-chat-${stamp}.md`
  a.click()
  URL.revokeObjectURL(url)
}
