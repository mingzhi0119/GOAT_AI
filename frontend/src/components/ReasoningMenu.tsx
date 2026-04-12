import {
  useCallback,
  useEffect,
  useRef,
  type CSSProperties,
  type KeyboardEvent,
  type RefObject,
} from 'react'
import { CheckIcon, reasoningLabel, type ReasoningLevel } from './chatComposerPrimitives'

interface ReasoningMenuProps {
  isOpen: boolean
  isNarrow: boolean
  menuId: string
  triggerRef?: RefObject<HTMLButtonElement | null>
  focusStrategy: 'selected' | 'first' | 'last'
  reasoningLevel: ReasoningLevel
  onClose: () => void
  onSelectReasoningLevel: (level: ReasoningLevel) => void
}

const menuStyle = {
  borderColor: 'var(--input-border)',
  background: 'var(--composer-menu-bg)',
  backdropFilter: 'blur(14px)',
  boxShadow: '0 10px 20px rgba(15,23,42,0.08)',
} satisfies CSSProperties

export default function ReasoningMenu({
  isOpen,
  isNarrow,
  menuId,
  triggerRef,
  focusStrategy,
  reasoningLevel,
  onClose,
  onSelectReasoningLevel,
}: ReasoningMenuProps) {
  const levels = ['low', 'medium', 'high'] as const
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([])
  const selectedIndex = Math.max(levels.indexOf(reasoningLevel), 0)

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
    if (!isOpen) return
    const initialIndex =
      focusStrategy === 'first'
        ? 0
        : focusStrategy === 'last'
          ? levels.length - 1
          : selectedIndex
    const timer = window.setTimeout(() => focusItem(initialIndex), 0)
    return () => window.clearTimeout(timer)
  }, [focusItem, focusStrategy, isOpen, levels.length, selectedIndex])

  if (!isOpen) return null

  const handleSelect = (level: ReasoningLevel) => {
    onSelectReasoningLevel(level)
    onClose()
    restoreTriggerFocus()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = itemRefs.current.findIndex(node => node === document.activeElement)
    switch (event.key) {
      case 'ArrowDown': {
        event.preventDefault()
        focusItem(currentIndex >= 0 ? (currentIndex + 1) % levels.length : 0)
        break
      }
      case 'ArrowUp': {
        event.preventDefault()
        focusItem(currentIndex >= 0 ? (currentIndex - 1 + levels.length) % levels.length : levels.length - 1)
        break
      }
      case 'Home': {
        event.preventDefault()
        focusItem(0)
        break
      }
      case 'End': {
        event.preventDefault()
        focusItem(levels.length - 1)
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
      className={`absolute bottom-14 z-30 min-w-[148px] rounded-2xl border p-1.5 ${isNarrow ? 'left-[7.25rem] w-[min(44vw,10rem)]' : 'left-[152px]'}`}
      style={menuStyle}
      role="menu"
      aria-label="Reasoning menu"
      onKeyDown={handleKeyDown}
    >
      {levels.map((level, index) => {
        const isSelected = level === reasoningLevel
        return (
          <button
            key={level}
            ref={node => {
              itemRefs.current[index] = node
            }}
            type="button"
            role="menuitemradio"
            aria-checked={isSelected}
            onClick={() => handleSelect(level)}
            className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
            style={{ color: 'var(--text-main)' }}
          >
            <span className="font-medium">{reasoningLabel(level)}</span>
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
