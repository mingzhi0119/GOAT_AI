import type { Message } from '../api/types'

/** Build a Markdown document from chat messages and trigger download. */
export function downloadChatAsMarkdown(messages: Message[], title?: string | null): void {
  const completed = messages.filter(m => !m.isStreaming && m.content.trim().length > 0)
  if (completed.length === 0) {
    window.alert('No messages to export.')
    return
  }
  const header = title?.trim() || 'GOAT AI conversation'
  const lines: string[] = [`# ${header}`, '']
  for (const m of completed) {
    const label = m.role === 'user' ? 'User' : 'Assistant'
    lines.push(`## ${label}`, '', m.content.trim(), '')
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  const a = document.createElement('a')
  a.href = url
  a.download = `goat-chat-${stamp}.md`
  a.click()
  URL.revokeObjectURL(url)
}
