import { useCallback } from 'react'
import { clearStoredProtectedAccess } from '../api/auth'

export interface UseOwnerIdReturn {
  ownerId: string
  setOwnerId: (value: string) => void
}

/** Deprecated no-op hook kept for compatibility while demo deployments stay public. */
export function useOwnerId(): UseOwnerIdReturn {
  const setOwnerId = useCallback((value: string) => {
    void value
    clearStoredProtectedAccess()
  }, [])

  return { ownerId: '', setOwnerId }
}
