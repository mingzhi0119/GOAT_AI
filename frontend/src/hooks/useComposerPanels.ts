import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type RefObject } from 'react'

export type ComposerPanel = 'plus' | 'manage-uploads' | 'model' | 'reasoning' | 'code-sandbox' | null
export type MenuFocusStrategy = 'selected' | 'first' | 'last'

interface UseComposerPanelsArgs {
  panelBoundaryRef: RefObject<HTMLDivElement | null>
  plusButtonRef: RefObject<HTMLButtonElement | null>
  stopCodeSandboxMonitoring: () => void
}

interface UseComposerPanelsReturn {
  activePanel: ComposerPanel
  plusMenuOpen: boolean
  manageUploadsOpen: boolean
  modelMenuOpen: boolean
  reasoningMenuOpen: boolean
  codeSandboxOpen: boolean
  modelMenuFocusStrategy: MenuFocusStrategy
  reasoningMenuFocusStrategy: MenuFocusStrategy
  setActivePanel: (panel: ComposerPanel) => void
  closeActivePanel: () => void
  toggleComposerPanel: (panel: Exclude<ComposerPanel, null>) => void
  toggleModelMenu: () => void
  toggleReasoningMenu: () => void
  handleModelMenuTriggerKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
  handleReasoningMenuTriggerKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
}

function resolveFocusStrategy(key: string): MenuFocusStrategy | null {
  if (key === 'ArrowDown') return 'first'
  if (key === 'ArrowUp') return 'last'
  return null
}

export function useComposerPanels({
  panelBoundaryRef,
  plusButtonRef,
  stopCodeSandboxMonitoring,
}: UseComposerPanelsArgs): UseComposerPanelsReturn {
  const [activePanel, setActivePanelState] = useState<ComposerPanel>(null)
  const [modelMenuFocusStrategy, setModelMenuFocusStrategy] =
    useState<MenuFocusStrategy>('selected')
  const [reasoningMenuFocusStrategy, setReasoningMenuFocusStrategy] =
    useState<MenuFocusStrategy>('selected')
  const previousUtilityPanelOpenRef = useRef(false)
  const previousCodeSandboxPanelOpenRef = useRef(false)

  const setActivePanel = useCallback((panel: ComposerPanel) => {
    setActivePanelState(panel)
  }, [])

  const closeActivePanel = useCallback(() => {
    setActivePanelState(null)
  }, [])

  const toggleComposerPanel = useCallback((panel: Exclude<ComposerPanel, null>) => {
    setActivePanelState(previous => (previous === panel ? null : panel))
  }, [])

  const toggleModelMenu = useCallback(() => {
    setModelMenuFocusStrategy('selected')
    toggleComposerPanel('model')
  }, [toggleComposerPanel])

  const toggleReasoningMenu = useCallback(() => {
    setReasoningMenuFocusStrategy('selected')
    toggleComposerPanel('reasoning')
  }, [toggleComposerPanel])

  const handleModelMenuTriggerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      const focusStrategy = resolveFocusStrategy(event.key)
      if (focusStrategy === null) return
      event.preventDefault()
      setModelMenuFocusStrategy(focusStrategy)
      setActivePanelState('model')
    },
    [],
  )

  const handleReasoningMenuTriggerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      const focusStrategy = resolveFocusStrategy(event.key)
      if (focusStrategy === null) return
      event.preventDefault()
      setReasoningMenuFocusStrategy(focusStrategy)
      setActivePanelState('reasoning')
    },
    [],
  )

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (!activePanel) return
      if (!panelBoundaryRef.current?.contains(event.target as Node)) {
        closeActivePanel()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [activePanel, closeActivePanel, panelBoundaryRef])

  const manageUploadsOpen = activePanel === 'manage-uploads'
  const codeSandboxOpen = activePanel === 'code-sandbox'

  useEffect(() => {
    const utilityPanelOpen = manageUploadsOpen || codeSandboxOpen
    if (!utilityPanelOpen && previousUtilityPanelOpenRef.current) {
      plusButtonRef.current?.focus()
    }
    previousUtilityPanelOpenRef.current = utilityPanelOpen
  }, [codeSandboxOpen, manageUploadsOpen, plusButtonRef])

  useEffect(() => {
    if (!codeSandboxOpen && previousCodeSandboxPanelOpenRef.current) {
      stopCodeSandboxMonitoring()
    }
    previousCodeSandboxPanelOpenRef.current = codeSandboxOpen
  }, [codeSandboxOpen, stopCodeSandboxMonitoring])

  return {
    activePanel,
    plusMenuOpen: activePanel === 'plus',
    manageUploadsOpen,
    modelMenuOpen: activePanel === 'model',
    reasoningMenuOpen: activePanel === 'reasoning',
    codeSandboxOpen,
    modelMenuFocusStrategy,
    reasoningMenuFocusStrategy,
    setActivePanel,
    closeActivePanel,
    toggleComposerPanel,
    toggleModelMenu,
    toggleReasoningMenu,
    handleModelMenuTriggerKeyDown,
    handleReasoningMenuTriggerKeyDown,
  }
}
