import { useCallback, useState } from 'react'
import { getStoredApiKey, setStoredApiKey } from '../api/auth'

const MAX_LEN = 256

export interface UseApiKeyReturn {
  apiKey: string
  setApiKey: (value: string) => void
}

/** Shared-secret key for protected API access; persisted locally per browser. */
export function useApiKey(): UseApiKeyReturn {
  const [apiKeyState, setApiKeyState] = useState<string>(() => getStoredApiKey())

  const setApiKey = useCallback((value: string) => {
    const next = value.length > MAX_LEN ? value.slice(0, MAX_LEN) : value
    setApiKeyState(next)
    setStoredApiKey(next)
  }, [])

  return { apiKey: apiKeyState, setApiKey }
}
