import type { ChatMessage } from './types'

export interface HistorySessionItem {
  id: string
  title: string
  model: string
  created_at: string
  updated_at: string
}

export interface HistorySessionDetail extends HistorySessionItem {
  messages: ChatMessage[]
}

export async function fetchHistory(): Promise<HistorySessionItem[]> {
  const resp = await fetch('./api/history')
  if (!resp.ok) throw new Error(`History API: HTTP ${resp.status}`)
  const data = (await resp.json()) as { sessions?: HistorySessionItem[] }
  return Array.isArray(data.sessions) ? data.sessions : []
}

export async function fetchSession(sessionId: string): Promise<HistorySessionDetail> {
  const resp = await fetch(`./api/history/${encodeURIComponent(sessionId)}`)
  if (!resp.ok) throw new Error(`History session API: HTTP ${resp.status}`)
  return (await resp.json()) as HistorySessionDetail
}

export async function deleteSession(sessionId: string): Promise<void> {
  const resp = await fetch(`./api/history/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
  if (!resp.ok) throw new Error(`Delete history API: HTTP ${resp.status}`)
}
