const ABSOLUTE_URL_PATTERN = /^[a-z][a-z0-9+.-]*:\/\//i

/**
 * Normalize internal API paths to root-relative `/api/...` URLs.
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

  if (normalized === '/api' || normalized.startsWith('/api/')) {
    return normalized
  }
  if (normalized === 'api' || normalized.startsWith('api/')) {
    return `/${normalized}`
  }
  if (normalized.startsWith('/')) {
    return `/api${normalized}`
  }
  return `/api/${normalized}`
}
