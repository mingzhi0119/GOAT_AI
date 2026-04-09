import { useEffect, useState } from 'react'
import type { ChatLayoutMode } from '../utils/chatLayout'

const NARROW_LAYOUT_BREAKPOINT_PX = 768

function resolveChatLayoutMode(
  viewportWidth: number,
  explicitMode?: ChatLayoutMode,
): ChatLayoutMode {
  if (explicitMode) return explicitMode
  return viewportWidth < NARROW_LAYOUT_BREAKPOINT_PX ? 'narrow' : 'wide'
}

function getViewportWidth(): number {
  if (typeof window === 'undefined') {
    return NARROW_LAYOUT_BREAKPOINT_PX + 1
  }
  return window.innerWidth
}

/** Resolve the current chat-shell layout mode without turning it into device detection. */
export function useChatLayoutMode(explicitMode?: ChatLayoutMode): {
  readonly layoutMode: ChatLayoutMode
} {
  const [layoutMode, setLayoutMode] = useState<ChatLayoutMode>(() =>
    resolveChatLayoutMode(getViewportWidth(), explicitMode),
  )

  useEffect(() => {
    if (explicitMode) {
      setLayoutMode(explicitMode)
      return
    }

    const handleResize = () => {
      setLayoutMode(resolveChatLayoutMode(window.innerWidth))
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [explicitMode])

  return { layoutMode }
}
