import { useId, useState, type CSSProperties, type FC } from 'react'
import type { GPUStatus } from '../api/system'

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

function buildTooltipLines(status: GPUStatus | null, gpuError: string | null): string[] {
  if (gpuError) return [`Error: ${gpuError}`]
  if (!status) return ['GPU telemetry unavailable']
  if (!status.available) return [status.message || 'GPU telemetry unavailable']
  const u = Math.round(status.utilization_gpu ?? 0)
  const engineState = status.active ? 'Active' : 'Idle'
  return [
    `Active(${u}% GPU)`,
    'Latency: Live',
    formatVramGb(status.memory_used_mb, status.memory_total_mb),
    `A100 Engine: ${engineState}`,
  ]
}

interface Props {
  gpuStatus: GPUStatus | null
  gpuError: string | null
}

/** Compact GPU status: colored dot; details only in hover/focus tooltip. */
const GpuStatusDot: FC<Props> = ({ gpuStatus, gpuError }) => {
  const [open, setOpen] = useState(false)
  const tipId = useId()
  const available = Boolean(gpuStatus?.available)
  const util = gpuStatus?.utilization_gpu ?? null
  const fill = utilizationTierColor(util, available && !gpuError)
  const lines = buildTooltipLines(gpuStatus, gpuError)
  const label =
    gpuError != null && gpuError !== ''
      ? `GPU error: ${gpuError}`
      : available
        ? `GPU ${Math.round(util ?? 0)}% utilization`
        : 'GPU telemetry unavailable'

  return (
    <div className="relative flex-shrink-0 self-center -translate-x-1">
      <button
        type="button"
        className="rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[var(--bg-chat)] focus:ring-yellow-500"
        aria-label={label}
        aria-describedby={open ? tipId : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        <span
          className="gpu-status-breathe block w-3 h-3 rounded-full border border-white/30 shadow-sm"
          style={
            {
              backgroundColor: fill,
              '--gpu-dot-fill': fill,
            } as CSSProperties
          }
        />
      </button>
      {open && (
        <div
          id={tipId}
          role="tooltip"
          className="absolute bottom-full left-0 mb-2 px-2.5 py-2 rounded-md text-xs text-left z-30 pointer-events-none shadow-lg border w-max max-w-[11rem] whitespace-normal leading-snug"
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
