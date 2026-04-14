import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
import {
  parseHistorySessionDetailResponse,
  parseHistorySessionListResponse,
} from './runtimeSchemas'
import type { HistorySessionDetail, HistorySessionItem } from './types'
import { buildApiUrl } from './urls'

export type { HistorySessionDetail, HistorySessionItem } from './types'

export async function fetchHistory(): Promise<HistorySessionItem[]> {
  const resp = await fetch(buildApiUrl('/history'), {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'History API'))
  return parseHistorySessionListResponse(await resp.json())
}

export async function fetchSession(sessionId: string): Promise<HistorySessionDetail> {
  const resp = await fetch(buildApiUrl(`/history/${encodeURIComponent(sessionId)}`), {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'History session API'))
  return parseHistorySessionDetailResponse(await resp.json())
}

export async function deleteSession(sessionId: string): Promise<void> {
  const resp = await fetch(buildApiUrl(`/history/${encodeURIComponent(sessionId)}`), {
    method: 'DELETE',
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Delete history API'))
}

export async function deleteAllSessions(): Promise<void> {
  const resp = await fetch(buildApiUrl('/history'), {
    method: 'DELETE',
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Delete all history API'))
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  const resp = await fetch(buildApiUrl(`/history/${encodeURIComponent(sessionId)}`), {
    method: 'PATCH',
    headers: buildApiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ title }),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Rename history API'))
}
