import { describe, expect, it } from 'vitest'
import { truncateSessionTitle } from '../utils/sessionTitle'

describe('truncateSessionTitle', () => {
  it('limits English titles to 26 characters including ellipsis', () => {
    expect(truncateSessionTitle('Frontier Macroeconomic Research Outlook')).toBe(
      'Frontier Macroeconomic...',
    )
  })

  it('limits Chinese titles to 15 characters including ellipsis', () => {
    expect(truncateSessionTitle('如何回复父亲的移民焦虑与就业前景担忧')).toBe('如何回复父亲的移民焦虑与...')
  })
})
