const ABSOLUTE_URL_PATTERN = /^[a-z][a-z0-9+.-]*:\/\//i

function resolveAgainstAppBase(path: string): string {
  if (typeof document === 'undefined' || !document.baseURI) {
    return `/${path}`
  }
  return new URL(path, document.baseURI).toString()
}

/**
 * Normalize internal API paths to app-relative `api/...` URLs so the SPA keeps
 * working behind sub-path proxies such as `/mingzhi/`.
 * Keeps absolute URLs unchanged so artifact downloads can still point elsewhere.
 */
export function buildApiUrl(path: string): string {
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
    return resolveAgainstAppBase('api')
  }
  if (normalized.startsWith('/api/')) {
    return resolveAgainstAppBase(normalized.slice(1))
  }
  if (normalized === 'api' || normalized.startsWith('api/')) {
    return resolveAgainstAppBase(normalized)
  }
  if (normalized.startsWith('/')) {
    return resolveAgainstAppBase(`api${normalized}`)
  }
  return resolveAgainstAppBase(`api/${normalized}`)
}
