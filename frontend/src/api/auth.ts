const API_KEY_STORAGE_KEY = 'goat-ai-api-key'
const OWNER_ID_STORAGE_KEY = 'goat-ai-owner-id'

function getStoredValue(storageKey: string): string {
  try {
    return (localStorage.getItem(storageKey) ?? '').trim()
  } catch {
    return ''
  }
}

function setStoredValue(storageKey: string, value: string): void {
  const trimmed = value.trim()
  try {
    if (trimmed) localStorage.setItem(storageKey, trimmed)
    else localStorage.removeItem(storageKey)
  } catch {
    // localStorage may be unavailable
  }
}

export function getStoredApiKey(): string {
  return getStoredValue(API_KEY_STORAGE_KEY)
}

export function getStoredOwnerId(): string {
  return getStoredValue(OWNER_ID_STORAGE_KEY)
}

export function buildApiHeaders(extraHeaders?: Record<string, string>): Record<string, string> {
  clearStoredProtectedAccess()
  return { ...(extraHeaders ?? {}) }
}

export function setStoredApiKey(apiKey: string): void {
  setStoredValue(API_KEY_STORAGE_KEY, apiKey)
}

export function setStoredOwnerId(ownerId: string): void {
  setStoredValue(OWNER_ID_STORAGE_KEY, ownerId)
}

export function clearStoredProtectedAccess(): void {
  setStoredApiKey('')
  setStoredOwnerId('')
}

export { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY }
