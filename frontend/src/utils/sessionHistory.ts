import type { HistorySessionDetail } from '../api/history'
import type { Message } from '../api/types'

export const FILE_CONTEXT_REPLY = 'I have loaded the file context.'

export function hydrateHistorySession(session: HistorySessionDetail): Message[] {
  const mapped: Message[] = []

  const fileContextPrompt = session.file_context?.prompt?.trim()
  if (fileContextPrompt) {
    mapped.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: fileContextPrompt,
      hidden: true,
    })
    mapped.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: FILE_CONTEXT_REPLY,
      hidden: true,
    })
  }

  for (const message of session.messages) {
    if (message.role !== 'user' && message.role !== 'assistant') continue
    mapped.push({
      id: crypto.randomUUID(),
      role: message.role,
      content: message.content,
    })
  }

  return mapped
}
