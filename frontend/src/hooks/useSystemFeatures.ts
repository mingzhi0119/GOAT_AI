import { useEffect, useState } from 'react'
import { fetchSystemFeatures, type SystemFeatures } from '../api/system'

interface UseSystemFeaturesReturn {
  features: SystemFeatures | null
  error: string | null
  refreshNow: () => Promise<void>
}

export function useSystemFeatures(): UseSystemFeaturesReturn {
  const [features, setFeatures] = useState<SystemFeatures | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshNow = async () => {
    try {
      setFeatures(await fetchSystemFeatures())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load system features')
    }
  }

  useEffect(() => {
    void refreshNow()
  }, [])

  return {
    features,
    error,
    refreshNow,
  }
}
