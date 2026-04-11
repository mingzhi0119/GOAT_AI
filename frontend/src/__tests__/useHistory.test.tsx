/* @vitest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useHistory } from '../hooks/useHistory'
import {
  deleteAllSessions,
  deleteSession,
  fetchHistory,
  fetchSession,
  renameSession,
} from '../api/history'
import type { HistorySessionDetail } from '../api/history'

vi.mock('../api/history', () => ({
  fetchHistory: vi.fn(),
  fetchSession: vi.fn(),
  deleteSession: vi.fn(),
  deleteAllSessions: vi.fn(),
  renameSession: vi.fn(),
}))

const sessionItem = {
  id: 'sess-1',
  title: 'First session',
  model: 'test-model',
  schema_version: 1,
  created_at: '2026-04-10T00:00:00Z',
  updated_at: '2026-04-10T00:00:00Z',
  owner_id: '',
}

describe('useHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads history on mount and supports local upsert/delete/rename flows', async () => {
    vi.mocked(fetchHistory).mockResolvedValue([sessionItem])
    vi.mocked(fetchSession).mockResolvedValue({
      ...sessionItem,
      messages: [],
      chart_spec: null,
      file_context: null,
      knowledge_documents: [],
      chart_data_source: null,
    })
    vi.mocked(deleteSession).mockResolvedValue(undefined)
    vi.mocked(renameSession).mockResolvedValue(undefined)
    vi.mocked(deleteAllSessions).mockResolvedValue(undefined)

    const { result } = renderHook(() => useHistory())

    await waitFor(() => expect(result.current.sessions).toHaveLength(1))

    let detail: HistorySessionDetail | undefined
    await act(async () => {
      detail = await result.current.loadSession('sess-1')
    })
    expect(detail?.id).toBe('sess-1')

    act(() => {
      result.current.upsertSession({ ...sessionItem, id: 'sess-2', title: 'Newest session' })
    })
    expect(result.current.sessions[0]?.id).toBe('sess-2')

    await act(async () => {
      await result.current.renameSession('sess-2', '  Renamed session  ')
    })
    expect(renameSession).toHaveBeenCalledWith('sess-2', 'Renamed session')
    expect(result.current.sessions[0]?.title).toBe('Renamed session')

    await act(async () => {
      await result.current.deleteSession('sess-2')
    })
    expect(deleteSession).toHaveBeenCalledWith('sess-2')
    expect(result.current.sessions).toHaveLength(1)

    await act(async () => {
      await result.current.deleteAll()
    })
    expect(deleteAllSessions).toHaveBeenCalled()
    expect(result.current.sessions).toEqual([])
  })

  it('surfaces refresh errors and ignores blank rename titles', async () => {
    vi.mocked(fetchHistory).mockRejectedValue(new Error('history unavailable'))

    const { result } = renderHook(() => useHistory())

    await waitFor(() => expect(result.current.error).toBe('history unavailable'))
    expect(result.current.sessions).toEqual([])

    await act(async () => {
      await result.current.renameSession('sess-1', '   ')
    })
    expect(renameSession).not.toHaveBeenCalled()
  })
})
