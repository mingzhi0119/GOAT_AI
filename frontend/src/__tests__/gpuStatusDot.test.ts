import { describe, expect, it } from 'vitest'
import { utilizationTierColor } from '../components/GpuStatusDot'

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
