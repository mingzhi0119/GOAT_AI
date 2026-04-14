import { buildApiErrorMessage } from './errors'
import { fetchApi } from './http'
import {
  parseModelCapabilitiesResponse,
  parseModelsResponse,
} from './runtimeSchemas'
import type { ModelCapabilitiesResponse, ModelsResponse } from './types'

/** Fetch the list of available Ollama model names from the backend. */
export async function fetchModels(): Promise<string[]> {
  const resp = await fetchApi('/models')
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Models API'))
  const data: ModelsResponse = parseModelsResponse(await resp.json())
  return data.models
}

/** Fetch Ollama-reported capabilities for one model. */
export async function fetchModelCapabilities(model: string): Promise<ModelCapabilitiesResponse> {
  const resp = await fetchApi(`/models/capabilities?model=${encodeURIComponent(model)}`)
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Model capabilities API'))
  }
  return parseModelCapabilitiesResponse(await resp.json())
}
