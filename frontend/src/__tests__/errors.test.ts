import { describe, expect, it } from 'vitest'
import { buildApiErrorMessage, extractApiErrorDetail } from '../api/errors'

describe('api error helpers', () => {
  it('extracts string and validation-array details', () => {
    expect(extractApiErrorDetail({ detail: 'Invalid API key.' })).toBe('Invalid API key.')
    expect(extractApiErrorDetail({ detail: [{ loc: ['body'], msg: 'bad', type: 'value_error' }] })).toBe(
      'Request validation failed.',
    )
    expect(extractApiErrorDetail({})).toBeNull()
  })

  it('includes stable code and request id metadata when present', async () => {
    const response = {
      status: 401,
      json: async () => ({
        detail: 'Invalid API key.',
        code: 'AUTH_INVALID_API_KEY',
        request_id: 'req-123',
      }),
    } as unknown as Response

    await expect(buildApiErrorMessage(response, 'Chat API')).resolves.toBe(
      'Invalid API key. [AUTH_INVALID_API_KEY; request req-123]',
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
