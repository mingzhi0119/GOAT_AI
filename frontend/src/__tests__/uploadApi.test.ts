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

  it('parses file_context events', async () => {
    const payload = [
      'data: {"type":"file_context","filename":"data.csv","prompt":"p"}\n',
      'data: {"type":"done"}\n',
    ].join('')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse(payload)))

    const events: unknown[] = []
    for await (const event of streamUpload(new File(['x,y\n1,2'], 'data.csv'))) {
      events.push(event)
    }
    expect(events).toHaveLength(2)
    expect((events[0] as { type: string }).type).toBe('file_context')
    expect((events[1] as { type: string }).type).toBe('done')
  })
})
