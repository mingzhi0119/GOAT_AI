const ABSOLUTE_URL_PATTERN = /^[a-z][a-z0-9+.-]*:\/\//i
const DESKTOP_BACKEND_ORIGIN = 'http://127.0.0.1:62606'

function resolveApiBaseUri(baseUri: string): string {
  const parsed = new URL(baseUri)
  if (
    parsed.protocol === 'asset:' ||
    parsed.protocol === 'tauri:' ||
    parsed.hostname === 'asset.localhost' ||
    parsed.hostname === 'tauri.localhost'
  ) {
    return DESKTOP_BACKEND_ORIGIN
  }
  return baseUri
}

function normalizeApiPath(path: string): string {
  const trimmed = path.trim()
  if (!trimmed) {
    throw new Error('API path is required')
  }
  if (ABSOLUTE_URL_PATTERN.test(trimmed) || trimmed.startsWith('//')) {
    return trimmed
  }

  let normalized = trimmed
  if (normalized.startsWith('./')) {
    normalized = normalized.slice(1)
  }

  if (normalized === '/api') {
    return 'api'
  }
  if (normalized.startsWith('/api/')) {
    return normalized.slice(1)
  }
  if (normalized === 'api' || normalized.startsWith('api/')) {
    return normalized
  }
  if (normalized.startsWith('/')) {
    return `api${normalized}`
  }
  return `api/${normalized}`
}

export function buildApiUrlFromBase(path: string, baseUri: string): string {
  const normalized = normalizeApiPath(path)
  if (ABSOLUTE_URL_PATTERN.test(normalized) || normalized.startsWith('//')) {
    return normalized
  }
  return new URL(normalized, resolveApiBaseUri(baseUri)).toString()
}

/**
 * Normalize internal API paths to app-relative `api/...` URLs so the SPA keeps
 * working behind sub-path proxies such as `/mingzhi/`.
 * Keeps absolute URLs unchanged so artifact downloads can still point elsewhere.
 */
export function buildApiUrl(path: string): string {
  if (typeof document === 'undefined' || !document.baseURI) {
    const normalized = normalizeApiPath(path)
    return ABSOLUTE_URL_PATTERN.test(normalized) || normalized.startsWith('//')
      ? normalized
      : `/${normalized}`
  }
  return buildApiUrlFromBase(path, document.baseURI)
}
