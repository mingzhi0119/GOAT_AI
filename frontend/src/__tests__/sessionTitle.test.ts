import { describe, expect, it } from 'vitest'
import { deriveSessionTitle } from '../hooks/useSessionTitle'
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

  it('prefers the persisted history title for the active session', () => {
    expect(
      deriveSessionTitle({
        sessionId: 'session-1',
        historySessions: [{ id: 'session-1', title: 'Saved title' }],
        messages: [
          {
            role: 'user',
            content: 'This would be ignored because history wins',
          },
        ],
      }),
    ).toBe('Saved title')
  })

  it('ignores hidden and streaming user messages when deriving the fallback title', () => {
    expect(
      deriveSessionTitle({
        sessionId: 'session-2',
        historySessions: [],
        messages: [
          {
            role: 'user',
            content: 'Hidden system bootstrap',
            hidden: true,
          },
          {
            role: 'user',
            content: 'Streaming draft',
            isStreaming: true,
          },
          {
            role: 'user',
            content: 'Visible user question that should become the fallback title',
          },
        ],
      }),
    ).toBe('Visible user question t...')
  })
})
