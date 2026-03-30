import { type FC, type MouseEvent } from 'react'
import FileUpload from './FileUpload'

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
        <span className="text-3xl select-none" aria-hidden="true">🐐</span>
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
              className="px-2.5 py-2 rounded-lg text-base transition-all disabled:opacity-40"
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
            className="w-full text-left px-3 py-2 rounded-lg text-sm transition-all"
            style={{ color: 'var(--text-sidebar)', background: 'transparent' }}
            {...hoverHandlers('var(--sidebar-hover)')}
          >
            🗑&nbsp; Clear Chat
          </button>

          <button
            type="button"
            onClick={onToggleTheme}
            className="w-full text-left px-3 py-2 rounded-lg text-sm transition-all"
            style={{ color: 'var(--text-sidebar)', background: 'transparent' }}
            {...hoverHandlers('var(--sidebar-hover)')}
          >
            {theme === 'light' ? '🌙' : '☀️'}&nbsp;{' '}
            {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
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

      {/* ── Footer ───────────────────────────────────────────────── */}
      <div
        className="flex-shrink-0 px-5 py-4"
        style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}
      >
        <p className="text-xs" style={{ color: 'rgba(255,255,255,0.38)' }}>
          Powered by{' '}
          <span style={{ color: 'var(--gold)' }}>Mingzhi Hu</span>
        </p>
      </div>
    </aside>
  )
}

export default Sidebar
