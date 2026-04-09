import { describe, expect, it } from 'vitest'
import { getChatLayoutDecisions } from '../utils/chatLayout'

describe('chat layout decisions', () => {
  it('returns docked desktop decisions for wide mode', () => {
    expect(getChatLayoutDecisions('wide')).toEqual({
      layoutMode: 'wide',
      sidebarBehavior: 'docked',
      compactTopBar: false,
      compactComposer: false,
      compactSpacing: false,
      singleColumnPrompts: false,
      expandedMessageWidth: false,
    })
  })

  it('returns overlay-focused mobile decisions for narrow mode', () => {
    expect(getChatLayoutDecisions('narrow')).toEqual({
      layoutMode: 'narrow',
      sidebarBehavior: 'overlay',
      compactTopBar: true,
      compactComposer: true,
      compactSpacing: true,
      singleColumnPrompts: true,
      expandedMessageWidth: true,
    })
  })
})
