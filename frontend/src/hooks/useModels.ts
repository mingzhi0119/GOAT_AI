import { useCallback, useEffect, useState } from 'react'
import { fetchModelCapabilities, fetchModels } from '../api/models'
import type { ModelCapabilitiesResponse } from '../api/types'

const DEFAULT_MODEL = 'qwen3:4b'

export interface UseModelsReturn {
  models: string[]
  selectedModel: string
  setSelectedModel: (model: string) => void
  isLoading: boolean
  isLoadingCapabilities: boolean
  error: string | null
  capabilities: ModelCapabilitiesResponse | null
  capabilitiesError: string | null
  refresh: () => void
}

/** Fetches and manages the list of available Ollama models. */
export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [capabilities, setCapabilities] = useState<ModelCapabilitiesResponse | null>(null)
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const list = await fetchModels()
      setModels(list)
      // Keep existing selection when it still exists; otherwise prefer the repo default.
      setSelectedModel(prev => {
        if (prev && list.includes(prev)) {
          return prev
        }
        if (list.includes(DEFAULT_MODEL)) {
          return DEFAULT_MODEL
        }
        return list[0] ?? ''
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!selectedModel) {
      setCapabilities(null)
      setCapabilitiesError(null)
      return
    }

    let cancelled = false
    setIsLoadingCapabilities(true)
    setCapabilitiesError(null)

    void fetchModelCapabilities(selectedModel)
      .then(result => {
        if (!cancelled) {
          setCapabilities(result)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setCapabilities(null)
          setCapabilitiesError(
            err instanceof Error ? err.message : 'Failed to load model capabilities',
          )
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingCapabilities(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedModel])

  return {
    models,
    selectedModel,
    setSelectedModel,
    isLoading,
    isLoadingCapabilities,
    error,
    capabilities,
    capabilitiesError,
    refresh: load,
  }
}
