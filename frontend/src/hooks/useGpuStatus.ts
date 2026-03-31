import { useEffect, useState } from 'react'
import { fetchGpuStatus, type GPUStatus } from '../api/system'

const POLL_MS = 5000

export interface UseGpuStatusReturn {
  status: GPUStatus | null
  error: string | null
}

export function useGpuStatus(): UseGpuStatusReturn {
  const [status, setStatus] = useState<GPUStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const next = await fetchGpuStatus()
        if (cancelled) return
        setStatus(next)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to fetch GPU status')
      }
    }
    void load()
    const timer = window.setInterval(() => void load(), POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  return { status, error }
}
