export interface GPUStatus {
  available: boolean
  active: boolean
  message: string
  name: string
  uuid: string
  utilization_gpu: number | null
  memory_used_mb: number | null
  memory_total_mb: number | null
  temperature_c: number | null
  power_draw_w: number | null
}

export interface InferenceLatency {
  chat_avg_ms: number
  chat_sample_count: number
}

export async function fetchGpuStatus(): Promise<GPUStatus> {
  const resp = await fetch('./api/system/gpu')
  if (!resp.ok) throw new Error(`GPU status API: HTTP ${resp.status}`)
  return (await resp.json()) as GPUStatus
}

export async function fetchInferenceLatency(): Promise<InferenceLatency> {
  const resp = await fetch('./api/system/inference')
  if (!resp.ok) throw new Error(`Inference latency API: HTTP ${resp.status}`)
  return (await resp.json()) as InferenceLatency
}
