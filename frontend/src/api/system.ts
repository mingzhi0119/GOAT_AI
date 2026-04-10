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
  chat_p50_ms: number
  chat_p95_ms: number
  first_token_avg_ms: number
  first_token_sample_count: number
  first_token_p50_ms: number
  first_token_p95_ms: number
  model_buckets: Record<
    string,
    {
      chat_avg_ms: number
      chat_p50_ms: number
      chat_p95_ms: number
      chat_sample_count: number
      first_token_avg_ms: number
      first_token_p50_ms: number
      first_token_p95_ms: number
      first_token_sample_count: number
    }
  >
}

export interface CodeSandboxFeature {
  policy_allowed: boolean
  allowed_by_config: boolean
  available_on_host: boolean
  effective_enabled: boolean
  deny_reason: string | null
}

export interface SystemFeatures {
  code_sandbox: CodeSandboxFeature
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

export async function fetchSystemFeatures(): Promise<SystemFeatures> {
  const resp = await fetch('./api/system/features')
  if (!resp.ok) throw new Error(`System features API: HTTP ${resp.status}`)
  return (await resp.json()) as SystemFeatures
}
