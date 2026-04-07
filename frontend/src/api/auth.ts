const STORAGE_KEY = 'goat-ai-api-key'

export function getStoredApiKey(): string {
  try {
    return (localStorage.getItem(STORAGE_KEY) ?? '').trim()
  } catch {
    return ''
  }
}

export function buildApiHeaders(extraHeaders?: Record<string, string>): Record<string, string> {
  const headers = { ...(extraHeaders ?? {}) }
  const apiKey = getStoredApiKey()
  if (apiKey) headers['X-GOAT-API-Key'] = apiKey
  return headers
}

export function setStoredApiKey(apiKey: string): void {
  const trimmed = apiKey.trim()
  try {
    if (trimmed) localStorage.setItem(STORAGE_KEY, trimmed)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // localStorage may be unavailable
  }
}

export { STORAGE_KEY as API_KEY_STORAGE_KEY }
