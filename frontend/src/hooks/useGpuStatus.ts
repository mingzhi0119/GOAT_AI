import { useEffect, useState } from 'react'
import { fetchGpuStatus, type GPUStatus } from '../api/system'

/** Poll interval while the model is streaming vs idle (ms). */
const POLL_STREAMING_MS = 1000
const POLL_IDLE_MS = 10000

export interface UseGpuStatusReturn {
  status: GPUStatus | null
  error: string | null
}

export function useGpuStatus(isStreaming: boolean): UseGpuStatusReturn {
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
    const pollMs = isStreaming ? POLL_STREAMING_MS : POLL_IDLE_MS
    const timer = window.setInterval(() => void load(), pollMs)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [isStreaming])

  return { status, error }
}
