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

export async function fetchGpuStatus(): Promise<GPUStatus> {
  const resp = await fetch('./api/system/gpu')
  if (!resp.ok) throw new Error(`GPU status API: HTTP ${resp.status}`)
  return (await resp.json()) as GPUStatus
}
