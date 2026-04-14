import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { streamChat } from '../api/chat'
import type { ChatRequest } from '../api/types'
import { buildApiUrl } from '../api/urls'

function buildStreamResponse(chunks: string[]) {
  const encoder = new TextEncoder()
  return {
    ok: true,
    body: new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk))
        }
        controller.close()
      },
    }),
  }
}

const request: ChatRequest = {
  model: 'test-model',
  messages: [{ role: 'user', content: 'Hello' }],
}

describe('chat api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('parses chunked SSE frames into typed stream events', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildStreamResponse([
          'data: {"type":"token","token":"Hel',
          'lo"}\n\n',
          'data: {"type":"artifact","artifact_id":"art-1","filename":"brief.md","mime_type":"text/markdown","byte_size":12,"download_url":"/api/artifacts/art-1"}\n\n',
          'data: {"type":"chart_spec","chart":{"version":"2.0","engine":"echarts","kind":"line","title":"Trend","description":"","dataset":[],"option":{},"meta":{"row_count":0,"truncated":false,"warnings":[],"source_columns":[]}}}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      ),
    )

    const events = []
    for await (const event of streamChat(request, { userName: 'Simon' })) {
      events.push(event)
    }

    expect(events).toEqual([
      { type: 'token', token: 'Hello' },
      {
        type: 'artifact',
        artifact_id: 'art-1',
        filename: 'brief.md',
        mime_type: 'text/markdown',
        byte_size: 12,
        download_url: '/api/artifacts/art-1',
      },
      {
        type: 'chart_spec',
        chart: {
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
      },
      { type: 'done' },
    ])
    expect(fetch).toHaveBeenCalledWith(
      buildApiUrl('/chat'),
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'alice',
          'X-User-Name': 'Simon',
        },
      }),
    )
  })

  it('skips malformed SSE frames while keeping the stream alive', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildStreamResponse([
          'data: {"type":"chart_spec","chart":{"version":"2.0","engine":"echarts"}}\n\n',
          'data: {"type":"token","token":"Hello"}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      ),
    )

    const events = []
    for await (const event of streamChat(request)) {
      events.push(event)
    }

    expect(events).toEqual([{ type: 'token', token: 'Hello' }, { type: 'done' }])
  })

  it('throws for HTTP failures and missing response bodies', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status: 503 }))

    await expect(async () => {
      for await (const _event of streamChat(request)) {
        // consume
      }
    }).rejects.toThrow('Chat API: HTTP 503')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: true,
        body: null,
      }),
    )

    await expect(async () => {
      for await (const _event of streamChat(request)) {
        // consume
      }
    }).rejects.toThrow('Chat API: no response body')
  })

  it('treats fetch aborts as a silent stop', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new DOMException('Aborted', 'AbortError')),
    )

    const events = []
    for await (const event of streamChat(request)) {
      events.push(event)
    }

    expect(events).toEqual([])
  })
})
