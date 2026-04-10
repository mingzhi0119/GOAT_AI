import { useEffect, useRef, useState, type FC } from 'react'
import type { ChatLayoutMode } from '../utils/chatLayout'

interface Props {
  sessionTitle: string | null
  hasSession: boolean
  modelCapabilities: string[] | null
  appearanceSummary: string
  layoutMode?: ChatLayoutMode
  onSidebarToggle?: () => void
  onOpenAppearance: () => void
  systemInstruction: string
  onSystemInstructionChange: (value: string) => void
  onExportMarkdown: () => void
  onDeleteConversation: () => void
  advancedOpen: boolean
  onAdvancedOpenChange: (open: boolean) => void
  temperature: number
  onTemperatureChange: (v: number) => void
  maxTokens: number
  onMaxTokensChange: (v: number) => void
  topP: number
  onTopPChange: (v: number) => void
  onResetAdvanced: () => void
}

const MAX_INSTRUCTION_LEN = 1000

/** Upper bound for `max_tokens` in ChatRequest; must match backend `ChatRequest.max_tokens` le=. */
const API_MAX_GENERATION_TOKENS = 131_072

function formatSkillLabel(capability: string): string | null {
  const normalized = capability.trim().toLowerCase()
  if (!normalized || normalized === 'completion') return null
  if (normalized === 'tools' || normalized === 'tool_calling') return 'Tools'
  if (normalized === 'vision') return 'Vision'
  if (normalized === 'audio' || normalized === 'sound' || normalized === 'speech') return 'Sound'
  if (normalized === 'images' || normalized === 'image') return 'Vision'
  return normalized
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map(part => part[0]!.toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
}

const TopBar: FC<Props> = ({
  sessionTitle,
  hasSession,
  modelCapabilities,
  appearanceSummary,
  layoutMode = 'wide',
  onSidebarToggle,
  onOpenAppearance,
  systemInstruction,
  onSystemInstructionChange,
  onExportMarkdown,
  onDeleteConversation,
  advancedOpen,
  onAdvancedOpenChange,
  temperature,
  onTemperatureChange,
  maxTokens,
  onMaxTokensChange,
  topP,
  onTopPChange,
  onResetAdvanced,
}) => {
  const [optionsOpen, setOptionsOpen] = useState(false)
  const [actionsOpen, setActionsOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const isNarrow = layoutMode === 'narrow'
  const skillLabels = (modelCapabilities ?? []).map(formatSkillLabel).filter(
    (label): label is string => Boolean(label),
  )

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOptionsOpen(false)
        setActionsOpen(false)
      }
    }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [])

  const fieldCls =
    'w-full rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-sky-500/35 cursor-text select-text'
  const actionButtonCls =
    'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]'
  return (
    <header
      className={`z-20 flex h-12 flex-shrink-0 items-center ${isNarrow ? 'gap-2 px-2.5' : 'px-3'}`}
      style={{
        background: 'var(--bg-chat)',
      }}
    >
      {isNarrow ? (
        <button
          type="button"
          aria-label="Open sidebar"
          className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full transition-all hover:opacity-90"
          style={{
            color: 'var(--text-main)',
            background: 'var(--composer-muted-surface)',
          }}
          onClick={onSidebarToggle}
        >
          <SidebarToggleIcon />
        </button>
      ) : (
        <div className="hidden" aria-hidden="true" />
      )}
      <div className="flex min-w-0 flex-1 items-center gap-3 px-1 select-none cursor-default">
        <h1
          className="max-w-full truncate text-left text-sm font-medium select-none cursor-default"
          style={{
            color: 'var(--text-main)',
          }}
          title={sessionTitle ?? undefined}
        >
          {sessionTitle ?? 'New conversation'}
        </h1>
        {skillLabels.length > 0 && (
          <div className="flex min-w-0 flex-wrap items-center gap-1.5 select-none cursor-default">
            {skillLabels.map(label => (
              <span
                key={label}
                className="inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium"
                style={{
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-main)',
                  background: 'var(--composer-muted-surface)',
                }}
              >
                {label}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="flex min-w-0 flex-shrink-0 justify-end" ref={wrapRef}>
        <div className="relative flex items-center gap-2">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full transition-all hover:opacity-90"
            style={{
              color: 'var(--text-main)',
              background: 'var(--composer-muted-surface)',
            }}
            aria-label="Conversation actions"
            aria-expanded={actionsOpen}
            aria-haspopup="menu"
            onClick={e => {
              e.stopPropagation()
              setActionsOpen(open => !open)
              setOptionsOpen(false)
            }}
          >
            <MoreIcon />
          </button>
          {actionsOpen && (
            <div
              className={`absolute right-0 top-full z-50 mt-2 rounded-2xl border p-1.5 shadow-[0_10px_20px_rgba(15,23,42,0.08)] ${isNarrow ? 'w-[min(92vw,20rem)]' : 'w-[332px]'}`}
              style={{
                borderColor: 'var(--input-border)',
                background: 'var(--composer-menu-bg)',
                backdropFilter: 'blur(14px)',
                boxShadow: '0 10px 20px rgba(15,23,42,0.08)',
              }}
              role="menu"
              aria-label="Conversation actions"
              onClick={e => e.stopPropagation()}
            >
              <button
                type="button"
                role="menuitem"
                className={actionButtonCls}
                style={{ color: 'var(--text-main)' }}
                onClick={() => {
                  onExportMarkdown()
                  setActionsOpen(false)
                }}
              >
                <span>
                  <span className="block font-medium leading-none">Export to Markdown</span>
                  <span className="block pt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    Save the current conversation as a Markdown file
                  </span>
                </span>
                <ChevronRightIcon />
              </button>
              <button
                type="button"
                role="menuitem"
                disabled={!hasSession}
                className={`${actionButtonCls} mt-0.5 ${hasSession ? '' : 'cursor-not-allowed opacity-50'}`}
                style={{ color: hasSession ? 'var(--text-main)' : 'var(--text-muted)' }}
                onClick={() => {
                  if (!hasSession) return
                  onDeleteConversation()
                  setActionsOpen(false)
                }}
              >
                <span>
                  <span className="block font-medium leading-none">Delete</span>
                  <span className="block pt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    Remove this saved conversation
                  </span>
                </span>
                <ChevronRightIcon />
              </button>
            </div>
          )}

          <div className="relative">
            <button
              type="button"
              className={`inline-flex items-center gap-2 rounded-full font-medium transition-all hover:opacity-90 ${isNarrow ? 'px-2.5 py-1.5 text-[13px]' : 'px-3 py-1.5 text-sm'}`}
              style={{
                color: 'var(--text-main)',
                background: 'var(--composer-muted-surface)',
              }}
              aria-label="Options"
              aria-expanded={optionsOpen}
              aria-haspopup="dialog"
              onClick={e => {
                e.stopPropagation()
                setOptionsOpen(o => !o)
                setActionsOpen(false)
              }}
            >
              <OptionsIcon />
              <span>Options</span>
            </button>

            {optionsOpen && (
            <div
              className={`absolute right-0 z-50 mt-2 max-h-[min(85vh,38rem)] overflow-y-auto rounded-[24px] border px-4 py-3 shadow-[0_16px_36px_var(--panel-shadow-color)] ${isNarrow ? 'w-[min(96vw,22rem)]' : 'w-[min(92vw,26rem)]'}`}
              style={{
                background: 'var(--composer-menu-bg-strong)',
                borderColor: 'var(--input-border)',
                color: 'var(--text-main)',
                backdropFilter: 'blur(18px)',
              }}
              role="dialog"
              aria-label="Options"
              onClick={e => e.stopPropagation()}
            >
              <div className="space-y-3">
                <section className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-muted)' }}>
                        Instructions
                      </p>
                    </div>
                    <button
                      type="button"
                      className="rounded-full border px-2.5 py-1 text-[11px]"
                      style={{
                        borderColor: 'var(--border-color)',
                        color: 'var(--text-muted)',
                      }}
                      onClick={() => onSystemInstructionChange('')}
                    >
                      Clear
                    </button>
                  </div>
                  <textarea
                    id="goat-system-instruction"
                    rows={3}
                    maxLength={MAX_INSTRUCTION_LEN}
                    value={systemInstruction}
                    onChange={e => onSystemInstructionChange(e.target.value)}
                    placeholder="Optional: tone, format, or constraints for the model"
                    className={`${fieldCls} min-h-[4.5rem] resize-y`}
                    style={{
                      background: 'var(--input-bg)',
                      border: '1px solid var(--input-border)',
                      color: 'var(--text-main)',
                    }}
                  />
                  <p
                    className="mt-1 text-right text-[10px]"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {systemInstruction.length}/{MAX_INSTRUCTION_LEN}
                  </p>
                </section>

                <section
                  className="border-t pt-3"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-muted)' }}>
                        Generation
                      </p>
                      <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                        Tune generation behavior for this chat.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="rounded-full border px-2.5 py-1 text-[11px]"
                      style={{
                        borderColor: 'var(--border-color)',
                        color: 'var(--text-muted)',
                      }}
                      aria-label="Reset generation settings to defaults"
                      onClick={() => {
                        onResetAdvanced()
                        onAdvancedOpenChange(true)
                      }}
                    >
                      Reset
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                    <div>
                      <label
                        className="mb-1 block text-[11px] font-medium"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        Temperature
                      </label>
                      <input
                        type="number"
                        step={0.05}
                        min={0}
                        max={2}
                        value={temperature}
                        onChange={e => {
                          const v = parseFloat(e.target.value)
                          if (!Number.isNaN(v)) onTemperatureChange(Math.min(2, Math.max(0, v)))
                        }}
                        className={fieldCls}
                        style={{
                          background: 'var(--input-bg)',
                          border: '1px solid var(--input-border)',
                          color: 'var(--text-main)',
                        }}
                      />
                    </div>
                    <div>
                      <label
                        className="mb-1 block text-[11px] font-medium"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        Max tokens
                      </label>
                      <input
                        type="number"
                        step={1}
                        min={1}
                        value={maxTokens}
                        onChange={e => {
                          const v = parseInt(e.target.value, 10)
                          if (!Number.isNaN(v)) {
                            onMaxTokensChange(
                              Math.min(API_MAX_GENERATION_TOKENS, Math.max(1, v)),
                            )
                          }
                        }}
                        className={fieldCls}
                        style={{
                          background: 'var(--input-bg)',
                          border: '1px solid var(--input-border)',
                          color: 'var(--text-main)',
                        }}
                      />
                    </div>
                    <div>
                      <label
                        className="mb-1 block text-[11px] font-medium"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        Top P
                      </label>
                      <input
                        type="number"
                        step={0.05}
                        min={0}
                        max={1}
                        value={topP}
                        onChange={e => {
                          const v = parseFloat(e.target.value)
                          if (!Number.isNaN(v)) onTopPChange(Math.min(1, Math.max(0, v)))
                        }}
                        className={fieldCls}
                        style={{
                          background: 'var(--input-bg)',
                          border: '1px solid var(--input-border)',
                          color: 'var(--text-main)',
                        }}
                      />
                    </div>
                  </div>
                </section>

                <section
                  className="border-t pt-3"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-muted)' }}>
                    Appearance
                  </p>
                  <button
                    type="button"
                    className="mt-1.5 flex w-full items-center justify-between rounded-2xl px-2 py-1.5 text-left text-sm transition-colors hover:bg-slate-900/[0.04]"
                    style={{
                      color: 'var(--text-main)',
                    }}
                    onClick={() => {
                      onOpenAppearance()
                      setOptionsOpen(false)
                    }}
                  >
                    <span className="inline-flex items-center gap-2">
                      <AppearanceIcon />
                      <span>Open Appearance</span>
                    </span>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {appearanceSummary}
                    </span>
                  </button>
                </section>
              </div>
            </div>
          )}
          </div>
        </div>
      </div>
    </header>
  )
}

const SidebarToggleIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M3.25 4.5h9.5M3.25 8h9.5M3.25 11.5h6.25"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
)

const OptionsIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M3.25 4.5h9.5M3.25 8h9.5M3.25 11.5h9.5"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
)

const MoreIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <circle cx="3.25" cy="8" r="1.1" fill="currentColor" />
    <circle cx="8" cy="8" r="1.1" fill="currentColor" />
    <circle cx="12.75" cy="8" r="1.1" fill="currentColor" />
  </svg>
)

const ChevronRightIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
    <path
      d="M5.25 3.5 8.75 7l-3.5 3.5"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const AppearanceIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 1.75a6.25 6.25 0 1 0 0 12.5c1.61 0 2.68-.49 3.4-1.15.68-.63.61-1.66-.2-2.1l-.58-.31c-.82-.44-.95-1.52-.28-2.14l1.24-1.16a1.65 1.65 0 0 0 .37-1.9A6.25 6.25 0 0 0 8 1.75Z"
      stroke="currentColor"
      strokeWidth="1.3"
    />
    <circle cx="5.1" cy="6.1" r=".8" fill="currentColor" />
    <circle cx="7.95" cy="4.85" r=".8" fill="currentColor" />
    <circle cx="5.8" cy="9.25" r=".8" fill="currentColor" />
  </svg>
)

export default TopBar
