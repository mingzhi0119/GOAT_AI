import type { HistorySessionDetail } from '../api/history'
import type { ChartSpec, HistorySessionMessage, Message } from '../api/types'

type UiHistoryMessage = {
  role: 'user' | 'assistant'
  content: string
}

export const FILE_CONTEXT_PREFIXES = [
  '[User uploaded tabular data for analysis]',
  '[User requested analysis of uploaded tabular data]',
] as const

export const FILE_CONTEXT_REPLY = 'I have loaded the file context.'
export const STORED_CHART_ROLE = '__chart__' as const
export const STORED_FILE_CONTEXT_ROLE = '__file_context__' as const
export const STORED_FILE_CONTEXT_ACK_ROLE = '__file_context_ack__' as const

export function parseStoredChartSpec(session: HistorySessionDetail): ChartSpec | null {
  const chartMessages = session.messages.filter(message => message.role === STORED_CHART_ROLE)
  const lastChart = chartMessages[chartMessages.length - 1]
  if (!lastChart) return null
  try {
    return JSON.parse(lastChart.content) as ChartSpec
  } catch {
    return null
  }
}

export function hydrateVisibleMessages(sessionMessages: HistorySessionMessage[]): Message[] {
  const uiRows: UiHistoryMessage[] = sessionMessages.flatMap(message => {
    if (message.role === 'user' || message.role === 'assistant') {
      return [{ role: message.role, content: message.content }]
    }
    if (message.role === STORED_FILE_CONTEXT_ROLE) {
      return [{ role: 'user', content: message.content }]
    }
    if (message.role === STORED_FILE_CONTEXT_ACK_ROLE) {
      return [{ role: 'assistant', content: message.content }]
    }
    return []
  })

  const mapped: Message[] = []
  let index = 0
  while (index < uiRows.length) {
    const current = uiRows[index]
    if (!current) break

    const isFileContext =
      current.role === 'user' &&
      FILE_CONTEXT_PREFIXES.some(prefix => current.content.startsWith(prefix))

    if (isFileContext) {
      mapped.push({
        id: crypto.randomUUID(),
        role: 'user',
        content: current.content,
        hidden: true,
      })
      const next = uiRows[index + 1]
      if (next && next.role === 'assistant' && next.content === FILE_CONTEXT_REPLY) {
        mapped.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: next.content,
          hidden: true,
        })
        index += 2
        continue
      }
      index += 1
      continue
    }

    mapped.push({
      id: crypto.randomUUID(),
      role: current.role,
      content: current.content,
    })
    index += 1
  }

  return mapped
}
