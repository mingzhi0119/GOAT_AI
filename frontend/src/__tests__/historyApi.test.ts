import { afterEach, describe, expect, it, vi } from 'vitest'
import { deleteAllSessions, deleteSession, fetchHistory, fetchSession } from '../api/history'

describe('history api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches history list', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sessions: [{ id: 's1', title: 't', model: 'm', created_at: 'c', updated_at: 'u' }] }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const sessions = await fetchHistory()
    expect(sessions).toHaveLength(1)
    expect(mockedFetch).toHaveBeenCalledWith('./api/history')
  })

  it('fetches single session detail', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 's1',
        title: 't',
        model: 'm',
        created_at: 'c',
        updated_at: 'u',
        chart_spec: { version: '2.0', engine: 'echarts' },
        file_context: { prompt: 'prompt' },
        knowledge_documents: [{ document_id: 'doc-1', filename: 'strategy.pdf', mime_type: 'application/pdf' }],
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
    expect(detail.chart_spec).toEqual({ version: '2.0', engine: 'echarts' })
    expect(detail.file_context).toEqual({ prompt: 'prompt' })
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
    expect(mockedFetch).toHaveBeenCalledWith('./api/history/s1')
  })

  it('deletes a session', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', mockedFetch)

    await deleteSession('abc')
    expect(mockedFetch).toHaveBeenCalledWith('./api/history/abc', { method: 'DELETE' })
  })

  it('deletes all sessions', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', mockedFetch)

    await deleteAllSessions()
    expect(mockedFetch).toHaveBeenCalledWith('./api/history', { method: 'DELETE' })
  })
})
