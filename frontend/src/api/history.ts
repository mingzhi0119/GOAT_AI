import { buildApiHeaders } from './auth'
import type { HistorySessionDetail, HistorySessionItem } from './types'

export type { HistorySessionDetail, HistorySessionItem } from './types'

export async function fetchHistory(): Promise<HistorySessionItem[]> {
  const resp = await fetch('./api/history', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`History API: HTTP ${resp.status}`)
  const data = (await resp.json()) as { sessions?: HistorySessionItem[] }
  return Array.isArray(data.sessions) ? data.sessions : []
}

export async function fetchSession(sessionId: string): Promise<HistorySessionDetail> {
  const resp = await fetch(`./api/history/${encodeURIComponent(sessionId)}`, {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`History session API: HTTP ${resp.status}`)
  return (await resp.json()) as HistorySessionDetail
}

export async function deleteSession(sessionId: string): Promise<void> {
  const resp = await fetch(`./api/history/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`Delete history API: HTTP ${resp.status}`)
}

export async function deleteAllSessions(): Promise<void> {
  const resp = await fetch('./api/history', {
    method: 'DELETE',
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`Delete all history API: HTTP ${resp.status}`)
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  const resp = await fetch(`./api/history/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: buildApiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ title }),
  })
  if (!resp.ok) throw new Error(`Rename history API: HTTP ${resp.status}`)
}
