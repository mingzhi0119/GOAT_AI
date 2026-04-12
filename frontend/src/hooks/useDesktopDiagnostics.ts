import { useEffect, useState } from 'react'
import {
  fetchDesktopDiagnostics,
  type DesktopDiagnostics,
} from '../api/system'

interface UseDesktopDiagnosticsReturn {
  diagnostics: DesktopDiagnostics | null
  error: string | null
  refreshNow: () => Promise<void>
}

export function useDesktopDiagnostics(): UseDesktopDiagnosticsReturn {
  const [diagnostics, setDiagnostics] = useState<DesktopDiagnostics | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshNow = async () => {
    try {
      setDiagnostics(await fetchDesktopDiagnostics())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load desktop diagnostics')
    }
  }

  useEffect(() => {
    void refreshNow()
  }, [])

  return {
    diagnostics,
    error,
    refreshNow,
  }
}
