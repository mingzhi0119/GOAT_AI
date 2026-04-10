import { useId, useState, type CSSProperties, type FC } from 'react'
import type { GPUStatus, InferenceLatency } from '../api/system'

/** Map GPU utilization to traffic-light colors (green / yellow / red). */
export function utilizationTierColor(utilization: number | null, available: boolean): string {
  if (!available || utilization === null) return '#9ca3af'
  if (utilization < 50) return '#22c55e'
  if (utilization < 80) return '#eab308'
  return '#ef4444'
}

function formatVramGb(usedMb: number | null, totalMb: number | null): string {
  const u = (usedMb ?? 0) / 1024
  const t = (totalMb ?? 0) / 1024
  const fmt = (n: number) => (Number.isFinite(n) ? n.toFixed(n >= 100 ? 0 : 1) : '0')
  return `VRAM ${fmt(u)}GB/${fmt(t)}GB`
}

function buildTooltipLines(
  status: GPUStatus | null,
  gpuError: string | null,
  inference: InferenceLatency | null,
): string[] {
  if (gpuError) return [`Error: ${gpuError}`]
  if (!status) return ['GPU telemetry unavailable']
  if (!status.available) return [status.message || 'GPU telemetry unavailable']

  const u = Math.round(status.utilization_gpu ?? 0)
  const engineState = status.active ? 'Active' : 'Idle'
  const lines = [
    `Active(${u}% GPU)`,
    formatVramGb(status.memory_used_mb, status.memory_total_mb),
    `${status.name || 'GPU'}: ${engineState}`,
  ]

  if (inference && inference.chat_sample_count > 0) {
    lines.splice(
      1,
      0,
      `Latency: avg ${Math.round(inference.chat_avg_ms)} ms (last ${inference.chat_sample_count})`,
    )
  }

  return lines
}

interface Props {
  gpuStatus: GPUStatus | null
  gpuError: string | null
  inferenceLatency: InferenceLatency | null
}

/** Compact GPU status: hover-only dot; not clickable. */
const GpuStatusDot: FC<Props> = ({ gpuStatus, gpuError, inferenceLatency }) => {
  const [open, setOpen] = useState(false)
  const tipId = useId()
  const available = Boolean(gpuStatus?.available)
  const active = Boolean(gpuStatus?.active)

  if (!available || gpuError) return null

  const util = gpuStatus?.utilization_gpu ?? null
  const fill = utilizationTierColor(util, true)
  const lines = buildTooltipLines(gpuStatus, null, inferenceLatency)
  const isVisible = active
  const label = `GPU ${Math.round(util ?? 0)}% utilization`

  return (
    <div className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center self-center">
      <div
        className="rounded-full transition-opacity duration-200"
        role="img"
        aria-label={label}
        aria-describedby={open ? tipId : undefined}
        aria-hidden={!isVisible}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        style={{
          opacity: isVisible ? 0.92 : 0.3,
          pointerEvents: 'auto',
          cursor: 'default',
        }}
      >
        <span
          className={`${isVisible ? 'gpu-status-breathe' : ''} block h-2.5 w-2.5 rounded-full border border-white/25 shadow-sm`}
          style={
            {
              backgroundColor: fill,
              '--gpu-dot-fill': fill,
            } as CSSProperties
          }
        />
      </div>
      {open && (
        <div
          id={tipId}
          role="tooltip"
          className="absolute bottom-full left-0 mb-2 w-max max-w-[11rem] rounded-md border px-2.5 py-2 text-left text-xs leading-snug shadow-lg pointer-events-none whitespace-normal z-30"
          style={{
            background: 'var(--bg-asst-bubble)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-main)',
          }}
        >
          {lines.map((line, i) => (
            <p key={i} className={i > 0 ? 'mt-1' : ''}>
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export default GpuStatusDot
