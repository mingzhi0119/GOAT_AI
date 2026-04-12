import { useCallback, useState } from 'react'
import { getStoredOwnerId, setStoredOwnerId } from '../api/auth'

const MAX_LEN = 256

export interface UseOwnerIdReturn {
  ownerId: string
  setOwnerId: (value: string) => void
}

/** Optional session-owner header for protected multi-tenant chat/history deployments. */
export function useOwnerId(): UseOwnerIdReturn {
  const [ownerIdState, setOwnerIdState] = useState<string>(() => getStoredOwnerId())

  const setOwnerId = useCallback((value: string) => {
    const next = value.length > MAX_LEN ? value.slice(0, MAX_LEN) : value
    setOwnerIdState(next)
    setStoredOwnerId(next)
  }, [])

  return { ownerId: ownerIdState, setOwnerId }
}
