import { useCallback, useState } from 'react'
import type { OllamaOptionsPayload, ReasoningLevel } from '../api/types'

const STORAGE_TEMP = 'goat-ai-ollama-temperature'
const STORAGE_MAX = 'goat-ai-ollama-max-tokens'
const STORAGE_TOP_P = 'goat-ai-ollama-top-p'

const DEFAULT_TEMP = 0.8
const DEFAULT_MAX_TOKENS = 65536
const DEFAULT_TOP_P = 0.9
/** Must match backend `ChatRequest.max_tokens` maximum. */
const API_MAX_GENERATION_TOKENS = 131_072

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
  getOptionsForRequest: (think?: boolean | ReasoningLevel) => OllamaOptionsPayload
}

/** Advanced Ollama sampling options; persisted in localStorage. */
export function useAdvancedSettings(): UseAdvancedSettingsReturn {
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [temperature, setTemperatureState] = useState(() =>
    readNum(STORAGE_TEMP, DEFAULT_TEMP),
  )
  const [maxTokens, setMaxTokensState] = useState(() => {
    const raw = readNum(STORAGE_MAX, DEFAULT_MAX_TOKENS)
    return Math.min(API_MAX_GENERATION_TOKENS, Math.max(1, Math.floor(raw)))
  })
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
    const next = Math.min(
      API_MAX_GENERATION_TOKENS,
      Math.max(1, Math.floor(Number.isFinite(v) ? v : DEFAULT_MAX_TOKENS)),
    )
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

  const getOptionsForRequest = useCallback((think?: boolean | ReasoningLevel): OllamaOptionsPayload => {
    return {
      temperature,
      max_tokens: maxTokens,
      top_p: topP,
      ...(typeof think === 'boolean' ? { think } : {}),
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
