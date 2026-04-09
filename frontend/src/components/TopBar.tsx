import { useEffect, useRef, useState, type FC } from 'react'
import type { ChatLayoutMode } from '../utils/chatLayout'

interface Props {
  sessionTitle: string | null
  theme: 'light' | 'dark'
  layoutMode?: ChatLayoutMode
  onSidebarToggle?: () => void
  onToggleTheme: () => void
  systemInstruction: string
  onSystemInstructionChange: (value: string) => void
  onExportMarkdown: () => void
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

const TopBar: FC<Props> = ({
  sessionTitle,
  theme,
  layoutMode = 'wide',
  onSidebarToggle,
  onToggleTheme,
  systemInstruction,
  onSystemInstructionChange,
  onExportMarkdown,
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
  const [menuOpen, setMenuOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const isNarrow = layoutMode === 'narrow'

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [])

  const fieldCls =
    'w-full rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-sky-500/35 cursor-text select-text'
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
        <div className="min-w-0 flex-1" aria-hidden="true" />
      )}
      <div className={`flex min-w-0 ${isNarrow ? 'flex-1 justify-start' : 'flex-[2] justify-center px-2'}`}>
        <h1
          className={`max-w-full truncate ${isNarrow ? 'text-left text-[13px]' : 'text-center text-sm'} font-medium`}
          style={{
            color: sessionTitle ? 'var(--text-main)' : 'var(--text-muted)',
          }}
          title={sessionTitle ?? undefined}
        >
          {sessionTitle ?? 'New conversation'}
        </h1>
      </div>
      <div className={`flex min-w-0 ${isNarrow ? 'flex-shrink-0 justify-end' : 'flex-1 justify-end'}`} ref={wrapRef}>
        <div className="relative">
          <button
            type="button"
            className={`inline-flex items-center gap-2 rounded-full font-medium transition-all hover:opacity-90 ${isNarrow ? 'px-2.5 py-1.5 text-[13px]' : 'px-3 py-1.5 text-sm'}`}
            style={{
              color: 'var(--text-main)',
              background: 'var(--composer-muted-surface)',
            }}
            aria-label="Options"
            aria-expanded={menuOpen}
            aria-haspopup="dialog"
            onClick={e => {
              e.stopPropagation()
              setMenuOpen(o => !o)
            }}
          >
            <OptionsIcon />
            <span>Options</span>
          </button>

          {menuOpen && (
            <div
              className={`absolute right-0 z-50 mt-2 max-h-[min(85vh,38rem)] overflow-y-auto rounded-[24px] border px-4 py-3 shadow-[0_16px_36px_rgba(15,23,42,0.12)] ${isNarrow ? 'w-[min(96vw,22rem)]' : 'w-[min(92vw,26rem)]'}`}
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
                        max={131072}
                        value={maxTokens}
                        onChange={e => {
                          const v = parseInt(e.target.value, 10)
                          if (!Number.isNaN(v)) onMaxTokensChange(Math.min(131072, Math.max(1, v)))
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
                    Conversation
                  </p>
                  <button
                    type="button"
                    className="mt-1.5 flex w-full items-center justify-between rounded-2xl px-2 py-1.5 text-left text-sm transition-colors hover:bg-slate-900/[0.04]"
                    style={{
                      color: 'var(--text-main)',
                    }}
                    onClick={() => {
                      onExportMarkdown()
                      setMenuOpen(false)
                    }}
                  >
                    <span>
                      <span className="block font-medium">Export Markdown</span>
                      <span className="mt-0.5 block text-xs" style={{ color: 'var(--text-muted)' }}>
                        Save the current conversation as a Markdown file.
                      </span>
                    </span>
                    <ChevronRightIcon />
                  </button>
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
                      onToggleTheme()
                      setMenuOpen(false)
                    }}
                  >
                    <span className="inline-flex items-center gap-2">
                      {theme === 'light' ? <MoonIcon /> : <SunIcon />}
                      <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
                    </span>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {theme === 'light' ? 'Switch to dark' : 'Switch to light'}
                    </span>
                  </button>
                </section>
              </div>
            </div>
          )}
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

const MoonIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z" />
  </svg>
)

const SunIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707z" />
  </svg>
)

export default TopBar
