import { afterEach, describe, expect, it, vi } from 'vitest'
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
    vi.restoreAllMocks()
  })

  it('parses knowledge_ready events', async () => {
    const payload = [
      'data: {"type":"knowledge_ready","filename":"data.csv","document_id":"doc-1","ingestion_id":"ing-1","status":"completed","retrieval_mode":"knowledge_rag"}\n',
      'data: {"type":"done"}\n',
    ].join('')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse(payload)))

    const events: unknown[] = []
    for await (const event of streamUpload(new File(['x,y\n1,2'], 'data.csv'))) {
      events.push(event)
    }
    expect(events).toHaveLength(2)
    expect((events[0] as { type: string }).type).toBe('knowledge_ready')
    expect((events[1] as { type: string }).type).toBe('done')
  })
})
