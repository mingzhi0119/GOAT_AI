import type { CSSProperties } from 'react'
import { CheckIcon, reasoningLabel, type ReasoningLevel } from './chatComposerPrimitives'

interface ReasoningMenuProps {
  isOpen: boolean
  isNarrow: boolean
  reasoningLevel: ReasoningLevel
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
  reasoningLevel,
  onSelectReasoningLevel,
}: ReasoningMenuProps) {
  if (!isOpen) return null

  return (
    <div
      className={`absolute bottom-14 z-30 min-w-[148px] rounded-2xl border p-1.5 ${isNarrow ? 'left-[7.25rem] w-[min(44vw,10rem)]' : 'left-[152px]'}`}
      style={menuStyle}
      role="menu"
      aria-label="Reasoning menu"
    >
      {(['low', 'medium', 'high'] as const).map(level => {
        const isSelected = level === reasoningLevel
        return (
          <button
            key={level}
            type="button"
            role="menuitemradio"
            aria-checked={isSelected}
            onClick={() => onSelectReasoningLevel(level)}
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
