import { describe, expect, it } from 'vitest'
import { buildApiUrl } from '../api/urls'

describe('buildApiUrl', () => {
  it('normalizes internal endpoints to root-relative api paths', () => {
    expect(buildApiUrl('/chat')).toBe('/api/chat')
    expect(buildApiUrl('history')).toBe('/api/history')
    expect(buildApiUrl('api/models')).toBe('/api/models')
  })

  it('upgrades legacy relative api paths without changing the endpoint', () => {
    expect(buildApiUrl('./api/system/features')).toBe('/api/system/features')
  })

  it('keeps absolute download urls unchanged', () => {
    expect(buildApiUrl('https://cdn.goat.com/artifacts/brief.md')).toBe(
      'https://cdn.goat.com/artifacts/brief.md',
    )
  })
})
