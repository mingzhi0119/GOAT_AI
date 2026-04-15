import { describe, expect, it } from 'vitest'
import { buildApiUrl, buildApiUrlFromBase } from '../api/urls'

describe('buildApiUrl', () => {
  it('normalizes internal endpoints to current-origin api paths', () => {
    window.history.replaceState({}, '', '/')

    expect(buildApiUrl('/chat')).toBe('http://localhost:3000/api/chat')
    expect(buildApiUrl('history')).toBe('http://localhost:3000/api/history')
    expect(buildApiUrl('api/models')).toBe('http://localhost:3000/api/models')
  })

  it('upgrades legacy relative api paths without changing the endpoint', () => {
    window.history.replaceState({}, '', '/')

    expect(buildApiUrl('./api/system/features')).toBe('http://localhost:3000/api/system/features')
  })

  it('keeps api requests under a sub-path proxy', () => {
    window.history.replaceState({}, '', '/mingzhi/')

    expect(buildApiUrl('/auth/session')).toBe('http://localhost:3000/mingzhi/api/auth/session')
  })

  it('routes packaged desktop app origins to the local backend', () => {
    expect(buildApiUrlFromBase('/auth/session', 'asset://localhost/index.html')).toBe(
      'http://127.0.0.1:62606/api/auth/session',
    )
    expect(buildApiUrlFromBase('/auth/session', 'https://asset.localhost/index.html')).toBe(
      'http://127.0.0.1:62606/api/auth/session',
    )
    expect(buildApiUrlFromBase('/auth/session', 'tauri://localhost/index.html')).toBe(
      'http://127.0.0.1:62606/api/auth/session',
    )
  })

  it('keeps absolute download urls unchanged', () => {
    expect(buildApiUrl('https://cdn.goat.com/artifacts/brief.md')).toBe(
      'https://cdn.goat.com/artifacts/brief.md',
    )
  })
})
