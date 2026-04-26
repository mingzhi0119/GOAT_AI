import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { deleteAllSessions, deleteSession, fetchHistory, fetchSession, renameSession } from '../api/history'
import { buildApiUrl } from '../api/urls'

describe('history api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('fetches history list', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        sessions: [
          {
            id: 's1',
            title: 't',
            model: 'm',
            schema_version: 2,
            created_at: 'c',
            updated_at: 'u',
            owner_id: 'alice',
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const sessions = await fetchHistory()
    expect(sessions).toHaveLength(1)
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/history'),
      expect.objectContaining({
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('fetches single session detail', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 's1',
        title: 't',
        model: 'm',
        schema_version: 2,
        created_at: 'c',
        updated_at: 'u',
        owner_id: 'alice',
        persona_snapshot: {
          theme_style: 'thu',
          system_instruction: 'Stay concise.',
        },
        chart_spec: {
          version: '2.0',
          engine: 'echarts',
          kind: 'line',
          title: 'Trend',
          description: '',
          dataset: [],
          option: {},
          meta: {
            row_count: 0,
            truncated: false,
            warnings: [],
            source_columns: [],
          },
        },
        file_context: { prompt: 'prompt' },
        knowledge_documents: [{ document_id: 'doc-1', filename: 'strategy.pdf', mime_type: 'application/pdf' }],
        workspace_outputs: [],
        chart_data_source: 'uploaded',
        messages: [
          {
            role: 'assistant',
            content: 'hi',
            artifacts: [
              {
                artifact_id: 'art-1',
                filename: 'brief.md',
                mime_type: 'text/markdown',
                byte_size: 128,
                download_url: '/api/artifacts/art-1',
              },
            ],
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const detail = await fetchSession('s1')
    expect(detail.id).toBe('s1')
    expect(detail.chart_spec).toEqual({
      version: '2.0',
      engine: 'echarts',
      kind: 'line',
      title: 'Trend',
      description: '',
      dataset: [],
      option: {},
      meta: {
        row_count: 0,
        truncated: false,
        warnings: [],
        source_columns: [],
      },
    })
    expect(detail.file_context).toEqual({ prompt: 'prompt' })
    expect(detail.persona_snapshot).toEqual({
      theme_style: 'thu',
      system_instruction: 'Stay concise.',
    })
    expect(detail.knowledge_documents).toEqual([
      { document_id: 'doc-1', filename: 'strategy.pdf', mime_type: 'application/pdf' },
    ])
    expect(detail.messages[0]?.artifacts).toEqual([
      {
        artifact_id: 'art-1',
        filename: 'brief.md',
        mime_type: 'text/markdown',
        byte_size: 128,
        download_url: '/api/artifacts/art-1',
      },
    ])
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/history/s1'),
      expect.objectContaining({
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('keeps an empty history list when sessions is omitted', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({}),
      }),
    )

    await expect(fetchHistory()).resolves.toEqual([])
  })

  it('normalizes optional history detail fields', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 's2',
          title: 'Second session',
          model: 'gemma4:26b',
          schema_version: 2,
          created_at: '2026-04-13T00:00:00Z',
          updated_at: '2026-04-13T00:00:01Z',
          owner_id: 'alice',
          messages: [],
        }),
      }),
    )

    const detail = await fetchSession('s2')

    expect(detail.chart_spec).toBeNull()
    expect(detail.persona_snapshot).toBeNull()
    expect(detail.file_context).toBeNull()
    expect(detail.knowledge_documents).toEqual([])
    expect(detail.workspace_outputs).toEqual([])
    expect(detail.chart_data_source).toBeNull()
  })

  it('rejects malformed history detail payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 's3',
          title: 'Bad session',
          model: 'gemma4:26b',
          schema_version: 2,
          created_at: '2026-04-13T00:00:00Z',
          updated_at: '2026-04-13T00:00:01Z',
          owner_id: 'alice',
          messages: 'bad',
        }),
      }),
    )

    await expect(fetchSession('s3')).rejects.toThrow(
      /History session API returned an invalid response payload/,
    )
  })

  it('deletes a session', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', mockedFetch)

    await deleteSession('abc')
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/history/abc'),
      expect.objectContaining({
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('deletes all sessions', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', mockedFetch)

    await deleteAllSessions()
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/history'),
      expect.objectContaining({
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('renames a session', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', mockedFetch)

    await renameSession('abc', 'New title')
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/history/abc'),
      expect.objectContaining({
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          'content-type': 'application/json',
        },
        body: JSON.stringify({ title: 'New title' }),
      }),
    )
  })
})
