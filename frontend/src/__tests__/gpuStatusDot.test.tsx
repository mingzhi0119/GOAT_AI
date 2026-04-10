import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import GpuStatusDot, { utilizationTierColor } from '../components/GpuStatusDot'

describe('utilizationTierColor', () => {
  it('returns gray when not available', () => {
    expect(utilizationTierColor(0, false)).toBe('#9ca3af')
    expect(utilizationTierColor(50, false)).toBe('#9ca3af')
  })

  it('returns green below 50%', () => {
    expect(utilizationTierColor(0, true)).toBe('#22c55e')
    expect(utilizationTierColor(49.9, true)).toBe('#22c55e')
  })

  it('returns yellow from 50% to below 80%', () => {
    expect(utilizationTierColor(50, true)).toBe('#eab308')
    expect(utilizationTierColor(79, true)).toBe('#eab308')
  })

  it('returns red at 80% and above', () => {
    expect(utilizationTierColor(80, true)).toBe('#ef4444')
    expect(utilizationTierColor(100, true)).toBe('#ef4444')
  })

  it('returns gray when utilization is null but marketed available', () => {
    expect(utilizationTierColor(null, true)).toBe('#9ca3af')
  })
})

describe('GpuStatusDot', () => {
  it('hides latency when inference stats are unavailable', () => {
    render(
      <GpuStatusDot
        gpuStatus={{
          available: true,
          active: true,
          message: 'A100: Active',
          name: 'A100',
          uuid: 'gpu-1',
          utilization_gpu: 40,
          memory_used_mb: 1000,
          memory_total_mb: 81920,
          temperature_c: 33,
          power_draw_w: 50,
        }}
        gpuError={null}
        inferenceLatency={null}
      />,
    )

    fireEvent.mouseEnter(screen.getByRole('img'))
    expect(screen.getByRole('tooltip')).toHaveTextContent('A100')
    expect(screen.queryByText(/Latency:/i)).not.toBeInTheDocument()
  })

  it('disappears when telemetry is unavailable', () => {
    const { container, rerender } = render(
      <GpuStatusDot gpuStatus={null} gpuError={null} inferenceLatency={null} />,
    )
    expect(container).toBeEmptyDOMElement()

    rerender(
      <GpuStatusDot
        gpuStatus={{
          available: false,
          active: false,
          message: 'Telemetry unavailable',
          name: '',
          uuid: '',
          utilization_gpu: null,
          memory_used_mb: null,
          memory_total_mb: null,
          temperature_c: null,
          power_draw_w: null,
        }}
        gpuError={null}
        inferenceLatency={null}
      />,
    )

    expect(container).toBeEmptyDOMElement()
  })
})
