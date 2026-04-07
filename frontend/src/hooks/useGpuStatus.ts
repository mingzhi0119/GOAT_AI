import { useCallback, useEffect, useState } from 'react'
import { fetchGpuStatus, fetchInferenceLatency, type GPUStatus, type InferenceLatency } from '../api/system'

/** Poll interval while the model is streaming vs idle (ms). */
const POLL_STREAMING_MS = 1000
const POLL_IDLE_MS = 3000

export interface UseGpuStatusReturn {
  status: GPUStatus | null
  inference: InferenceLatency | null
  error: string | null
  refreshNow: () => Promise<void>
}

export function useGpuStatus(isStreaming: boolean): UseGpuStatusReturn {
  const [status, setStatus] = useState<GPUStatus | null>(null)
  const [inference, setInference] = useState<InferenceLatency | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)

  const refreshNow = useCallback(async () => {
    setRefreshTick(tick => tick + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const [gpuR, infR] = await Promise.allSettled([fetchGpuStatus(), fetchInferenceLatency()])
      if (cancelled) return
      if (infR.status === 'fulfilled') {
        setInference(infR.value)
      } else {
        setInference(null)
      }
      if (gpuR.status === 'fulfilled') {
        setStatus(gpuR.value)
        setError(null)
      } else {
        setStatus(null)
        const reason = gpuR.reason
        setError(reason instanceof Error ? reason.message : 'Failed to fetch GPU status')
      }
    }
    void load()
    const pollMs = isStreaming ? POLL_STREAMING_MS : POLL_IDLE_MS
    const timer = window.setInterval(() => void load(), pollMs)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [isStreaming, refreshTick])

  return { status, inference, error, refreshNow }
}
