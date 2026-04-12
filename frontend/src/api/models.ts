import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
import type { ModelCapabilitiesResponse, ModelsResponse } from './types'

/** Fetch the list of available Ollama model names from the backend. */
export async function fetchModels(): Promise<string[]> {
  const resp = await fetch('./api/models', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Models API'))
  const data = (await resp.json()) as ModelsResponse
  return data.models
}

/** Fetch Ollama-reported capabilities for one model. */
export async function fetchModelCapabilities(model: string): Promise<ModelCapabilitiesResponse> {
  const resp = await fetch(`./api/models/capabilities?model=${encodeURIComponent(model)}`, {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Model capabilities API'))
  }
  return (await resp.json()) as ModelCapabilitiesResponse
}
