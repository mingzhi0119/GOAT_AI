import { buildApiHeaders } from './auth'
import type { GPUStatus, InferenceLatency, SystemFeatures } from './types'

export type { GPUStatus, InferenceLatency, SystemFeatures } from './types'

export async function fetchGpuStatus(): Promise<GPUStatus> {
  const resp = await fetch('./api/system/gpu', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`GPU status API: HTTP ${resp.status}`)
  return (await resp.json()) as GPUStatus
}

export async function fetchInferenceLatency(): Promise<InferenceLatency> {
  const resp = await fetch('./api/system/inference', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`Inference latency API: HTTP ${resp.status}`)
  return (await resp.json()) as InferenceLatency
}

export async function fetchSystemFeatures(): Promise<SystemFeatures> {
  const resp = await fetch('./api/system/features', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(`System features API: HTTP ${resp.status}`)
  return (await resp.json()) as SystemFeatures
}
