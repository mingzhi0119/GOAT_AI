import { useCallback, useState } from 'react'

const STORAGE_KEY = 'goat-ai-system-instruction'
const MAX_LEN = 8000

export interface UseSystemInstructionReturn {
  systemInstruction: string
  setSystemInstruction: (text: string) => void
}

/** Optional per-browser system instructions appended server-side after the base GOAT prompt. */
export function useSystemInstruction(): UseSystemInstructionReturn {
  const [systemInstruction, setSystemInstructionState] = useState<string>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) ?? ''
    } catch {
      return ''
    }
  })

  const setSystemInstruction = useCallback((text: string) => {
    const next = text.length > MAX_LEN ? text.slice(0, MAX_LEN) : text
    setSystemInstructionState(next)
    try {
      if (next.trim()) {
        localStorage.setItem(STORAGE_KEY, next)
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      // localStorage may be unavailable
    }
  }, [])

  return { systemInstruction, setSystemInstruction }
}

export function clearStoredSystemInstruction(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // localStorage may be unavailable
  }
}
