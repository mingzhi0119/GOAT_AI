import { type FC, type MouseEvent } from 'react'
import FileUpload from './FileUpload'
import GoatIcon from './GoatIcon'

interface Props {
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
  onRefreshModels: () => void
  onClearChat: () => void
  isLoadingModels: boolean
  modelsError: string | null
  onStream: (gen: AsyncGenerator<string>) => Promise<void>
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}

/** Hover helper: avoids inlining repeated mouse-event handlers */
function hoverHandlers(hoverBg: string, defaultBg = 'transparent') {
  return {
    onMouseEnter: (e: MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.background = hoverBg
    },
    onMouseLeave: (e: MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.background = defaultBg
    },
  }
}

/* ── Inline SVG icons (fixed 16×16 box keeps action rows pixel-aligned) ── */
const TrashIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
    <path fillRule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
  </svg>
)

const MoonIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z"/>
  </svg>
)

const SunIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707z"/>
  </svg>
)

/** Left sidebar: branding, model selector, actions, file upload, footer. */
const Sidebar: FC<Props> = ({
  models,
  selectedModel,
  onModelChange,
  onRefreshModels,
  onClearChat,
  isLoadingModels,
  modelsError,
  onStream,
  theme,
  onToggleTheme,
}) => {
  return (
    <aside
      className="flex flex-col w-64 flex-shrink-0 h-screen overflow-x-hidden"
      style={{ background: 'var(--bg-sidebar)' }}
    >
      {/* ── Logo ─────────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-3 px-5 pt-6 pb-5"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}
      >
        <GoatIcon size={38} />
        <div>
          <h1 className="font-extrabold text-lg leading-tight" style={{ color: 'var(--gold)' }}>
            GOAT AI
          </h1>
          <p className="text-xs leading-tight" style={{ color: 'rgba(255,255,255,0.5)' }}>
            Simon Business School
          </p>
        </div>
      </div>

      {/* ── Scrollable body ──────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">

        {/* Model selector */}
        <section>
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-2"
            style={{ color: 'rgba(255,255,255,0.45)' }}
          >
            Model
          </p>
          <div className="flex gap-1.5 min-w-0">
            <select
              value={selectedModel}
              onChange={e => onModelChange(e.target.value)}
              disabled={isLoadingModels || models.length === 0}
              className="flex-1 min-w-0 rounded-lg px-2.5 py-2 text-xs focus:outline-none truncate"
              style={{
                background: 'rgba(255,255,255,0.1)',
                color: 'var(--text-sidebar)',
                border: '1px solid rgba(255,255,255,0.18)',
              }}
              aria-label="Select AI model"
            >
              {isLoadingModels && <option>Loading…</option>}
              {!isLoadingModels && models.length === 0 && !modelsError && (
                <option>No models found</option>
              )}
              {models.map(m => (
                <option key={m} value={m} style={{ background: '#001e3c' }}>
                  {m}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={onRefreshModels}
              disabled={isLoadingModels}
              title="Refresh model list"
              className="flex-shrink-0 px-2.5 py-2 rounded-lg text-sm transition-all disabled:opacity-40"
              style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--text-sidebar)' }}
              {...hoverHandlers('rgba(255,255,255,0.18)', 'rgba(255,255,255,0.1)')}
            >
              {isLoadingModels ? '⟳' : '↺'}
            </button>
          </div>

          {modelsError && (
            <p className="text-xs mt-1" style={{ color: '#f87171' }}>
              {modelsError}
            </p>
          )}
        </section>

        {/* Action buttons */}
        <section className="space-y-1">
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-2"
            style={{ color: 'rgba(255,255,255,0.45)' }}
          >
            Actions
          </p>

          <button
            type="button"
            onClick={onClearChat}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all"
            style={{ color: 'var(--text-sidebar)', background: 'transparent' }}
            {...hoverHandlers('var(--sidebar-hover)')}
          >
            <span className="flex-shrink-0 flex items-center justify-center w-4">
              <TrashIcon />
            </span>
            <span>Clear Chat</span>
          </button>

          <button
            type="button"
            onClick={onToggleTheme}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all"
            style={{ color: 'var(--text-sidebar)', background: 'transparent' }}
            {...hoverHandlers('var(--sidebar-hover)')}
          >
            <span className="flex-shrink-0 flex items-center justify-center w-4">
              {theme === 'light' ? <MoonIcon /> : <SunIcon />}
            </span>
            <span>{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
          </button>
        </section>

        {/* File Upload */}
        <section>
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-2"
            style={{ color: 'rgba(255,255,255,0.45)' }}
          >
            Analyze File
          </p>
          <FileUpload model={selectedModel} onStream={onStream} />
        </section>
      </div>

      {/* ── Footer: school logo + attribution ────────────────────── */}
      <div
        className="flex-shrink-0 px-5 py-4 space-y-3"
        style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}
      >
        {/* Simon Business School horizontal logo */}
        <img
          src="./simon_logo.svg"
          alt="Simon Business School — University of Rochester"
          className="w-full max-w-[148px]"
          style={{
            filter: 'brightness(0) invert(1)',
            opacity: 0.55,
          }}
        />

        <p className="text-xs" style={{ color: 'rgba(255,255,255,0.38)' }}>
          Powered by{' '}
          <span style={{ color: 'var(--gold)' }}>Mingzhi Hu</span>
        </p>
      </div>
    </aside>
  )
}

export default Sidebar
