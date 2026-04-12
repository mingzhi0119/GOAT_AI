import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type RefObject } from 'react'

export type TopBarPanel = 'actions' | 'settings' | null
export type TopBarMenuFocusStrategy = 'first' | 'last'

interface UseTopBarPanelsArgs {
  panelBoundaryRef: RefObject<HTMLDivElement | null>
  actionsTriggerRef: RefObject<HTMLButtonElement | null>
  settingsTriggerRef: RefObject<HTMLButtonElement | null>
}

interface ClosePanelOptions {
  restoreFocus?: boolean
}

interface OpenActionsOptions {
  focusStrategy?: TopBarMenuFocusStrategy
}

interface UseTopBarPanelsReturn {
  activePanel: TopBarPanel
  actionsOpen: boolean
  settingsOpen: boolean
  actionsFocusStrategy: TopBarMenuFocusStrategy
  openActionsPanel: (options?: OpenActionsOptions) => void
  openSettingsPanel: () => void
  togglePanel: (panel: Exclude<TopBarPanel, null>, options?: OpenActionsOptions) => void
  closeActivePanel: (options?: ClosePanelOptions) => void
  handleActionsTriggerKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
  handleSettingsTriggerKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
}

function focusTrigger(ref: RefObject<HTMLButtonElement | null> | null) {
  if (!ref?.current) return
  window.setTimeout(() => ref.current?.focus(), 0)
}

export function useTopBarPanels({
  panelBoundaryRef,
  actionsTriggerRef,
  settingsTriggerRef,
}: UseTopBarPanelsArgs): UseTopBarPanelsReturn {
  const [activePanel, setActivePanel] = useState<TopBarPanel>(null)
  const [actionsFocusStrategy, setActionsFocusStrategy] =
    useState<TopBarMenuFocusStrategy>('first')
  const restoreFocusRef = useRef<RefObject<HTMLButtonElement | null> | null>(null)

  const openActionsPanel = useCallback(
    (options?: OpenActionsOptions) => {
      restoreFocusRef.current = actionsTriggerRef
      setActionsFocusStrategy(options?.focusStrategy ?? 'first')
      setActivePanel('actions')
    },
    [actionsTriggerRef],
  )

  const openSettingsPanel = useCallback(() => {
    restoreFocusRef.current = settingsTriggerRef
    setActivePanel('settings')
  }, [settingsTriggerRef])

  const closeActivePanel = useCallback((options?: ClosePanelOptions) => {
    const restoreTarget = restoreFocusRef.current
    setActivePanel(null)
    if (options?.restoreFocus !== false) {
      focusTrigger(restoreTarget)
    }
  }, [])

  const togglePanel = useCallback(
    (panel: Exclude<TopBarPanel, null>, options?: OpenActionsOptions) => {
      if (panel === 'actions') {
        if (activePanel === 'actions') {
          closeActivePanel({ restoreFocus: false })
          return
        }
        openActionsPanel(options)
        return
      }

      if (activePanel === 'settings') {
        closeActivePanel({ restoreFocus: false })
        return
      }
      openSettingsPanel()
    },
    [activePanel, closeActivePanel, openActionsPanel, openSettingsPanel],
  )

  const handleActionsTriggerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault()
          openActionsPanel({ focusStrategy: 'first' })
          break
        case 'ArrowUp':
          event.preventDefault()
          openActionsPanel({ focusStrategy: 'last' })
          break
        case 'Enter':
        case ' ':
          event.preventDefault()
          togglePanel('actions')
          break
        default:
          break
      }
    },
    [openActionsPanel, togglePanel],
  )

  const handleSettingsTriggerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        togglePanel('settings')
      }
    },
    [togglePanel],
  )

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (!activePanel) return
      if (!panelBoundaryRef.current?.contains(event.target as Node)) {
        closeActivePanel({ restoreFocus: false })
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [activePanel, closeActivePanel, panelBoundaryRef])

  return {
    activePanel,
    actionsOpen: activePanel === 'actions',
    settingsOpen: activePanel === 'settings',
    actionsFocusStrategy,
    openActionsPanel,
    openSettingsPanel,
    togglePanel,
    closeActivePanel,
    handleActionsTriggerKeyDown,
    handleSettingsTriggerKeyDown,
  }
}
