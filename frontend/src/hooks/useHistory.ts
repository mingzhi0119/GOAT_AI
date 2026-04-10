import { useCallback, useEffect, useState } from 'react'
import {
  deleteAllSessions as deleteAllSessionsApi,
  deleteSession as deleteSessionApi,
  fetchHistory,
  fetchSession,
  type HistorySessionDetail,
  type HistorySessionItem,
} from '../api/history'

export interface UseHistoryReturn {
  sessions: HistorySessionItem[]
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
  upsertSession: (session: HistorySessionItem) => void
  loadSession: (sessionId: string) => Promise<HistorySessionDetail>
  deleteSession: (sessionId: string) => Promise<void>
  deleteAll: () => Promise<void>
}

export function useHistory(): UseHistoryReturn {
  const [sessions, setSessions] = useState<HistorySessionItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setSessions(await fetchHistory())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const loadSession = useCallback(async (sessionId: string) => fetchSession(sessionId), [])

  const upsertSession = useCallback((session: HistorySessionItem) => {
    setSessions(prev => {
      const remaining = prev.filter(item => item.id !== session.id)
      return [session, ...remaining]
    })
  }, [])

  const deleteSession = useCallback(
    async (sessionId: string) => {
      await deleteSessionApi(sessionId)
      setSessions(prev => prev.filter(item => item.id !== sessionId))
    },
    [],
  )

  const deleteAll = useCallback(async () => {
    await deleteAllSessionsApi()
    setSessions([])
  }, [])

  return {
    sessions,
    isLoading,
    error,
    refresh,
    upsertSession,
    loadSession,
    deleteSession,
    deleteAll,
  }
}
