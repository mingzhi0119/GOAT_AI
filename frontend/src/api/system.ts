import { buildApiErrorMessage } from './errors'
import { fetchApi } from './http'
import {
  parseDesktopDiagnosticsResponse,
  parseGpuStatusResponse,
  parseInferenceLatencyResponse,
  parseSystemFeaturesResponse,
} from './runtimeSchemas'
import type {
  DesktopDiagnostics,
  GPUStatus,
  InferenceLatency,
  SystemFeatures,
} from './types'

export type {
  DesktopDiagnostics,
  GPUStatus,
  InferenceLatency,
  SystemFeatures,
} from './types'

export async function fetchGpuStatus(): Promise<GPUStatus> {
  const resp = await fetchApi('/system/gpu')
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'GPU status API'))
  return parseGpuStatusResponse(await resp.json())
}

export async function fetchInferenceLatency(): Promise<InferenceLatency> {
  const resp = await fetchApi('/system/inference')
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Inference latency API'))
  }
  return parseInferenceLatencyResponse(await resp.json())
}

export async function fetchSystemFeatures(): Promise<SystemFeatures> {
  const resp = await fetchApi('/system/features')
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'System features API'))
  return parseSystemFeaturesResponse(await resp.json())
}

export async function fetchDesktopDiagnostics(): Promise<DesktopDiagnostics> {
  const resp = await fetchApi('/system/desktop')
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Desktop diagnostics API'))
  }
  return parseDesktopDiagnosticsResponse(await resp.json())
}
