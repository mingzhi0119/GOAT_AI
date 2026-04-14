import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { uploadMediaImage } from '../api/media'
import { buildApiUrl } from '../api/urls'

describe('media api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('uploads an image file through multipart form data', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        attachment_id: 'att-1',
        filename: 'chart.png',
        mime_type: 'image/png',
        byte_size: 12,
        width_px: 1,
        height_px: 1,
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const file = new File(['img'], 'chart.png', { type: 'image/png' })
    const payload = await uploadMediaImage(file)

    expect(payload.attachment_id).toBe('att-1')
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/media/uploads'),
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

  it('normalizes missing optional image dimensions', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          attachment_id: 'att-1',
          filename: 'chart.png',
          mime_type: 'image/png',
          byte_size: 12,
        }),
      }),
    )

    const file = new File(['img'], 'chart.png', { type: 'image/png' })
    const payload = await uploadMediaImage(file)

    expect(payload.width_px).toBeNull()
    expect(payload.height_px).toBeNull()
  })

  it('rejects malformed upload payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          attachment_id: 1,
          filename: 'chart.png',
          mime_type: 'image/png',
          byte_size: 12,
        }),
      }),
    )
    const file = new File(['img'], 'chart.png', { type: 'image/png' })

    await expect(uploadMediaImage(file)).rejects.toThrow(
      /Media upload API returned an invalid response payload/,
    )
  })

  it('throws a stable error on upload failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 413 }))
    const file = new File(['img'], 'chart.png', { type: 'image/png' })

    await expect(uploadMediaImage(file)).rejects.toThrow('Media upload API: HTTP 413')
  })
})
