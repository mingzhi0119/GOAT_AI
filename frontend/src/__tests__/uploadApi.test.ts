import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { streamUpload } from '../api/upload'

function sseResponse(lines: string): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(lines))
      controller.close()
    },
  })
  return new Response(stream, { status: 200 })
}

describe('upload api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('parses knowledge_ready events', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const payload = [
      'data: {"type":"file_prompt","filename":"data.csv","suffix_prompt":"Inspect this CSV for trends, anomalies, and key comparisons."}\n',
      'data: {"type":"knowledge_ready","filename":"data.csv","suffix_prompt":"Inspect this CSV for trends, anomalies, and key comparisons.","document_id":"doc-1","ingestion_id":"ing-1","status":"completed","retrieval_mode":"knowledge_rag","template_prompt":"Analyze this CSV and tell me the main trends, outliers, and comparisons worth noting."}\n',
      'data: {"type":"done"}\n',
    ].join('')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse(payload)))

    const events: unknown[] = []
    for await (const event of streamUpload(new File(['x,y\n1,2'], 'data.csv'))) {
      events.push(event)
    }
    expect(events).toHaveLength(3)
    expect((events[0] as { type: string }).type).toBe('file_prompt')
    expect((events[1] as { type: string }).type).toBe('knowledge_ready')
    expect((events[2] as { type: string }).type).toBe('done')
    expect(fetch).toHaveBeenCalledWith(
      './api/upload',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'alice',
        },
        body: expect.any(FormData),
      }),
    )
  })
})
