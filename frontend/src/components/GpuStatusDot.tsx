import { useId, useState, type FC } from 'react'
import type { GPUStatus } from '../api/system'

/** Map GPU utilization to traffic-light colors (green / yellow / red). */
export function utilizationTierColor(utilization: number | null, available: boolean): string {
  if (!available || utilization === null) return '#9ca3af'
  if (utilization < 50) return '#22c55e'
  if (utilization < 80) return '#eab308'
  return '#ef4444'
}

function buildTooltipLines(status: GPUStatus | null, gpuError: string | null): string[] {
  if (gpuError) return [`Error: ${gpuError}`]
  if (!status) return ['GPU telemetry unavailable']
  if (!status.available) return [status.message || 'GPU telemetry unavailable']
  const u = Math.round(status.utilization_gpu ?? 0)
  const name = status.name || 'GPU'
  const vramUsed = Math.round(status.memory_used_mb ?? 0)
  const vramTotal = Math.round(status.memory_total_mb ?? 0)
  return [
    `${name}: Active (${u}% GPU)`,
    `Latency: live | VRAM ${vramUsed}/${vramTotal} MB`,
    status.message ? status.message : '',
  ].filter(Boolean)
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
    <div className="relative flex-shrink-0 self-end pb-0.5">
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
          className="block w-3 h-3 rounded-full border border-white/30 shadow-sm"
          style={{ backgroundColor: fill }}
        />
      </button>
      {open && (
        <div
          id={tipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 rounded-md text-xs max-w-[min(90vw,18rem)] whitespace-pre-line text-left z-30 pointer-events-none shadow-lg border"
          style={{
            background: 'var(--bg-asst-bubble)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-main)',
          }}
        >
          {lines.map((line, i) => (
            <p key={i} className={i > 0 ? 'mt-0.5 opacity-90' : ''}>
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export default GpuStatusDot
