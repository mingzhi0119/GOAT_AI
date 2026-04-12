import {
  useCallback,
  useEffect,
  useRef,
  type CSSProperties,
  type KeyboardEvent,
  type RefObject,
} from 'react'
import { CheckIcon } from './chatComposerPrimitives'

interface ModelMenuProps {
  isOpen: boolean
  isNarrow: boolean
  menuId: string
  triggerRef?: RefObject<HTMLButtonElement | null>
  focusStrategy: 'selected' | 'first' | 'last'
  models: string[]
  selectedModel: string
  onClose: () => void
  onSelectModel: (model: string) => void
}

const menuStyle = {
  borderColor: 'var(--input-border)',
  background: 'var(--composer-menu-bg)',
  backdropFilter: 'blur(14px)',
  boxShadow: '0 10px 20px rgba(15,23,42,0.08)',
} satisfies CSSProperties

export default function ModelMenu({
  isOpen,
  isNarrow,
  menuId,
  triggerRef,
  focusStrategy,
  models,
  selectedModel,
  onClose,
  onSelectModel,
}: ModelMenuProps) {
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([])
  const selectedIndex = Math.max(models.indexOf(selectedModel), 0)

  const focusItem = useCallback(
    (index: number) => {
      itemRefs.current[index]?.focus()
    },
    [],
  )

  const restoreTriggerFocus = useCallback(() => {
    window.setTimeout(() => triggerRef?.current?.focus(), 0)
  }, [triggerRef])

  useEffect(() => {
    if (!isOpen || models.length === 0) return
    const initialIndex =
      focusStrategy === 'first'
        ? 0
        : focusStrategy === 'last'
          ? models.length - 1
          : selectedIndex
    const timer = window.setTimeout(() => focusItem(initialIndex), 0)
    return () => window.clearTimeout(timer)
  }, [focusItem, focusStrategy, isOpen, models.length, selectedIndex])

  if (!isOpen) return null

  const handleSelect = (model: string) => {
    onSelectModel(model)
    onClose()
    restoreTriggerFocus()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = itemRefs.current.findIndex(node => node === document.activeElement)
    switch (event.key) {
      case 'ArrowDown': {
        event.preventDefault()
        focusItem(currentIndex >= 0 ? (currentIndex + 1) % models.length : 0)
        break
      }
      case 'ArrowUp': {
        event.preventDefault()
        focusItem(currentIndex >= 0 ? (currentIndex - 1 + models.length) % models.length : models.length - 1)
        break
      }
      case 'Home': {
        event.preventDefault()
        focusItem(0)
        break
      }
      case 'End': {
        event.preventDefault()
        focusItem(models.length - 1)
        break
      }
      case 'Escape': {
        event.preventDefault()
        onClose()
        restoreTriggerFocus()
        break
      }
      case 'Tab': {
        onClose()
        break
      }
      default:
        break
    }
  }

  return (
    <div
      id={menuId}
      className={`absolute bottom-14 z-30 min-w-[180px] rounded-2xl border p-1.5 ${isNarrow ? 'left-9 w-[min(56vw,12rem)]' : 'left-10'}`}
      style={menuStyle}
      role="menu"
      aria-label="Model menu"
      onKeyDown={handleKeyDown}
    >
      {models.map((model, index) => {
        const isSelected = model === selectedModel
        return (
          <button
            key={model}
            ref={node => {
              itemRefs.current[index] = node
            }}
            type="button"
            role="menuitemradio"
            aria-checked={isSelected}
            onClick={() => handleSelect(model)}
            className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
            style={{ color: 'var(--text-main)' }}
          >
            <span className="truncate font-medium">{model}</span>
            <span
              className="ml-3 inline-flex h-4 w-4 items-center justify-center"
              style={{ color: isSelected ? 'var(--text-main)' : 'transparent' }}
            >
              <CheckIcon />
            </span>
          </button>
        )
      })}
    </div>
  )
}
