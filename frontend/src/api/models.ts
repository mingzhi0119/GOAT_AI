import type { ModelsResponse } from './types'

/** Fetch the list of available Ollama model names from the backend. */
export async function fetchModels(): Promise<string[]> {
  const resp = await fetch('./api/models')
  if (!resp.ok) throw new Error(`Models API: HTTP ${resp.status}`)
  const data = (await resp.json()) as ModelsResponse
  return data.models
}
