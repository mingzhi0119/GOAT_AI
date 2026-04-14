import { useCallback, useState } from 'react'

const STORAGE_KEY = 'goat-ai-username'

export interface UseUserNameReturn {
  userName: string
  setUserName: (name: string) => void
}

/** Persists an optional display name to localStorage for AI personalisation. */
export function useUserName(): UseUserNameReturn {
  const [userName, setUserNameState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? '',
  )

  const setUserName = useCallback((name: string) => {
    const trimmed = name.trim()
    setUserNameState(trimmed)
    if (trimmed) {
      localStorage.setItem(STORAGE_KEY, trimmed)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  return { userName, setUserName }
}

export function clearStoredUserName(): void {
  localStorage.removeItem(STORAGE_KEY)
}
