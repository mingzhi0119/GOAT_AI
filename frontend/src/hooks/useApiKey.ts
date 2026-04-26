import { useCallback } from 'react'
import { clearStoredProtectedAccess } from '../api/auth'

export interface UseApiKeyReturn {
  apiKey: string
  setApiKey: (value: string) => void
}

/** Deprecated no-op hook kept for compatibility while demo deployments stay public. */
export function useApiKey(): UseApiKeyReturn {
  const setApiKey = useCallback((value: string) => {
    void value
    clearStoredProtectedAccess()
  }, [])

  return { apiKey: '', setApiKey }
}
