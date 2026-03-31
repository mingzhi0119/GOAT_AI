import { useCallback, useState } from 'react'
import type { OllamaOptionsPayload } from '../api/types'

const STORAGE_TEMP = 'goat-ai-ollama-temperature'
const STORAGE_MAX = 'goat-ai-ollama-max-tokens'
const STORAGE_TOP_P = 'goat-ai-ollama-top-p'

const DEFAULT_TEMP = 0.8
const DEFAULT_MAX_TOKENS = 2048
const DEFAULT_TOP_P = 0.9

function readNum(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null || raw === '') return fallback
    const n = Number(raw)
    return Number.isFinite(n) ? n : fallback
  } catch {
    return fallback
  }
}

export interface UseAdvancedSettingsReturn {
  advancedOpen: boolean
  setAdvancedOpen: (open: boolean) => void
  temperature: number
  setTemperature: (v: number) => void
  maxTokens: number
  setMaxTokens: (v: number) => void
  topP: number
  setTopP: (v: number) => void
  /** Restore temperature / max tokens / top_p to defaults and persist. */
  resetAdvancedToDefaults: () => void
  getOptionsForRequest: () => OllamaOptionsPayload
}

/** Advanced Ollama sampling options; persisted in localStorage. */
export function useAdvancedSettings(): UseAdvancedSettingsReturn {
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [temperature, setTemperatureState] = useState(() =>
    readNum(STORAGE_TEMP, DEFAULT_TEMP),
  )
  const [maxTokens, setMaxTokensState] = useState(() =>
    readNum(STORAGE_MAX, DEFAULT_MAX_TOKENS),
  )
  const [topP, setTopPState] = useState(() => readNum(STORAGE_TOP_P, DEFAULT_TOP_P))

  const setTemperature = useCallback((v: number) => {
    const next = Number.isFinite(v) ? v : DEFAULT_TEMP
    setTemperatureState(next)
    try {
      localStorage.setItem(STORAGE_TEMP, String(next))
    } catch {
      /* ignore */
    }
  }, [])

  const setMaxTokens = useCallback((v: number) => {
    const next = Math.max(1, Math.floor(Number.isFinite(v) ? v : DEFAULT_MAX_TOKENS))
    setMaxTokensState(next)
    try {
      localStorage.setItem(STORAGE_MAX, String(next))
    } catch {
      /* ignore */
    }
  }, [])

  const setTopP = useCallback((v: number) => {
    const next = Number.isFinite(v) ? v : DEFAULT_TOP_P
    setTopPState(next)
    try {
      localStorage.setItem(STORAGE_TOP_P, String(next))
    } catch {
      /* ignore */
    }
  }, [])

  const resetAdvancedToDefaults = useCallback(() => {
    setTemperature(DEFAULT_TEMP)
    setMaxTokens(DEFAULT_MAX_TOKENS)
    setTopP(DEFAULT_TOP_P)
  }, [setTemperature, setMaxTokens, setTopP])

  const getOptionsForRequest = useCallback((): OllamaOptionsPayload => {
    return {
      temperature,
      max_tokens: maxTokens,
      top_p: topP,
    }
  }, [temperature, maxTokens, topP])

  return {
    advancedOpen,
    setAdvancedOpen,
    temperature,
    setTemperature,
    maxTokens,
    setMaxTokens,
    topP,
    setTopP,
    resetAdvancedToDefaults,
    getOptionsForRequest,
  }
}
