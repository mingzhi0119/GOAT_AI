import type { CSSProperties } from 'react'
import { CheckIcon } from './chatComposerPrimitives'

interface ModelMenuProps {
  isOpen: boolean
  isNarrow: boolean
  models: string[]
  selectedModel: string
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
  models,
  selectedModel,
  onSelectModel,
}: ModelMenuProps) {
  if (!isOpen) return null

  return (
    <div
      className={`absolute bottom-14 z-30 min-w-[180px] rounded-2xl border p-1.5 ${isNarrow ? 'left-9 w-[min(56vw,12rem)]' : 'left-10'}`}
      style={menuStyle}
      role="menu"
      aria-label="Model menu"
    >
      {models.map(model => {
        const isSelected = model === selectedModel
        return (
          <button
            key={model}
            type="button"
            role="menuitemradio"
            aria-checked={isSelected}
            onClick={() => onSelectModel(model)}
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
