import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
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
  const resp = await fetch('./api/system/gpu', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'GPU status API'))
  return (await resp.json()) as GPUStatus
}

export async function fetchInferenceLatency(): Promise<InferenceLatency> {
  const resp = await fetch('./api/system/inference', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Inference latency API'))
  }
  return (await resp.json()) as InferenceLatency
}

export async function fetchSystemFeatures(): Promise<SystemFeatures> {
  const resp = await fetch('./api/system/features', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'System features API'))
  return (await resp.json()) as SystemFeatures
}

export async function fetchDesktopDiagnostics(): Promise<DesktopDiagnostics> {
  const resp = await fetch('./api/system/desktop', {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Desktop diagnostics API'))
  }
  return (await resp.json()) as DesktopDiagnostics
}
