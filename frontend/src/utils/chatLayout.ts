export type ChatLayoutMode = 'wide' | 'narrow'

export interface ChatLayoutDecisions {
  readonly layoutMode: ChatLayoutMode
  readonly sidebarBehavior: 'docked' | 'overlay'
  readonly compactTopBar: boolean
  readonly compactComposer: boolean
  readonly compactSpacing: boolean
  readonly singleColumnPrompts: boolean
  readonly expandedMessageWidth: boolean
}

/** Map the current chat-shell layout mode to stable rendering decisions. */
export function getChatLayoutDecisions(layoutMode: ChatLayoutMode): ChatLayoutDecisions {
  if (layoutMode === 'narrow') {
    return {
      layoutMode,
      sidebarBehavior: 'overlay',
      compactTopBar: true,
      compactComposer: true,
      compactSpacing: true,
      singleColumnPrompts: true,
      expandedMessageWidth: true,
    }
  }

  return {
    layoutMode,
    sidebarBehavior: 'docked',
    compactTopBar: false,
    compactComposer: false,
    compactSpacing: false,
    singleColumnPrompts: false,
    expandedMessageWidth: false,
  }
}
