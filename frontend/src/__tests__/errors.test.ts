import { describe, expect, it } from 'vitest'
import { buildApiErrorMessage, extractApiErrorDetail } from '../api/errors'

describe('api error helpers', () => {
  it('extracts string and validation-array details', () => {
    expect(extractApiErrorDetail({ detail: 'Rate limit exceeded.' })).toBe('Rate limit exceeded.')
    expect(extractApiErrorDetail({ detail: [{ loc: ['body'], msg: 'bad', type: 'value_error' }] })).toBe(
      'Request validation failed.',
    )
    expect(extractApiErrorDetail({})).toBeNull()
  })

  it('includes stable code and request id metadata when present', async () => {
    const response = {
      status: 429,
      json: async () => ({
        detail: 'Rate limit exceeded.',
        code: 'RATE_LIMITED',
        request_id: 'req-123',
      }),
    } as unknown as Response

    await expect(buildApiErrorMessage(response, 'Chat API')).resolves.toBe(
      'Rate limit exceeded. [RATE_LIMITED; request req-123]',
    )
  })

  it('falls back to the HTTP label when no JSON body is available', async () => {
    const response = {
      status: 503,
      json: async () => {
        throw new Error('no body')
      },
    } as unknown as Response

    await expect(buildApiErrorMessage(response, 'Chat API')).resolves.toBe(
      'Chat API: HTTP 503',
    )
  })
})
