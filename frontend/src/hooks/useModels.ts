import { useCallback, useEffect, useState } from 'react'
import { fetchModels } from '../api/models'

const DEFAULT_MODEL = 'gemma4:26b'

export interface UseModelsReturn {
  models: string[]
  selectedModel: string
  setSelectedModel: (model: string) => void
  isLoading: boolean
  error: string | null
  refresh: () => void
}

/** Fetches and manages the list of available Ollama models. */
export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  return { models, selectedModel, setSelectedModel, isLoading, error, refresh: load }
}
