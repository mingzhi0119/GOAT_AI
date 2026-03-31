import { type FC, type MouseEvent } from 'react'
import FileUpload from './FileUpload'
import GoatIcon from './GoatIcon'
import type { HistorySessionItem } from '../api/history'
import type { ChartSpec } from '../api/types'
import type { FileContext } from '../hooks/useFileContext'
import {
  sidebarErrorTextClass,
  sidebarFileChipNameClass,
  sidebarFooterAttributionClass,
  sidebarFooterHighlightClass,
  sidebarHelperMutedClass,
  sidebarSectionLabelClass,
  sidebarSectionLabelRowClass,
  sidebarStaticBaseClass,
} from './sidebarStaticText'

interface Props {
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
  onRefreshModels: () => void
  onClearChat: () => void
  isLoadingModels: boolean
  modelsError: string | null
  onStream: (gen: AsyncGenerator<string>) => Promise<void>
  userName: string
  onUserNameChange: (name: string) => void
  historySessions: HistorySessionItem[]
  isLoadingHistory: boolean
  historyError: string | null
  onLoadHistorySession: (sessionId: string) => void
  onDeleteHistorySession: (sessionId: string) => void
  onRefreshHistory: () => void
  onDeleteAllHistory: () => void
  fileContext: FileContext | null
  onFileContext: (ctx: { type: 'file_context'; filename: string; prompt: string }) => void
  onChartSpec: (spec: ChartSpec) => void
  onClearFileContext: () => void
  /** Same optional system instruction as TopBar settings; applied to upload analysis. */
  systemInstruction: string
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
  userName,
  onUserNameChange,
  historySessions,
  isLoadingHistory,
  historyError,
  onLoadHistorySession,
  onDeleteHistorySession,
  onRefreshHistory,
  onDeleteAllHistory,
  fileContext,
  onFileContext,
  onChartSpec,
  onClearFileContext,
  systemInstruction,
}) => {
  const fmtDate = (value: string) => {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleString()
  }

  return (
    <aside
      className="flex flex-col w-64 flex-shrink-0 h-screen min-h-0 overflow-x-hidden"
      style={{ background: 'var(--bg-sidebar)' }}
    >
      {/* ── Logo (height matches TopBar h-12) ───────────────────── */}
      <div
        className="flex h-12 flex-shrink-0 items-center gap-2.5 px-4 border-b"
        style={{ borderColor: 'rgba(255,255,255,0.1)' }}
      >
        <GoatIcon size={28} />
        <h1
          className="text-base font-extrabold leading-none select-none cursor-default"
          style={{ color: 'var(--gold)' }}
        >
          GOAT AI
        </h1>
      </div>

      {/* ── Scrollable body ──────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">

        {/* Your name (optional) */}
        <section>
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
            Your Name
          </p>
          <input
            type="text"
            value={userName}
            onChange={e => onUserNameChange(e.target.value)}
            placeholder="Optional — AI will address you"
            maxLength={40}
            className="w-full rounded-lg px-2.5 py-2 text-xs focus:outline-none"
            style={{
              background: 'rgba(255,255,255,0.1)',
              color: 'var(--text-sidebar)',
              border: '1px solid rgba(255,255,255,0.18)',
            }}
          />
        </section>

        {/* Model selector */}
        <section>
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
            Model
          </p>
          <div className="flex gap-1.5 min-w-0">
            <select
              value={selectedModel}
              onChange={e => onModelChange(e.target.value)}
              disabled={isLoadingModels || models.length === 0}
              className="flex-1 min-w-0 rounded-lg px-2.5 py-2 text-xs focus:outline-none truncate cursor-pointer"
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
                <option key={m} value={m} style={{ background: '#001e3c', cursor: 'default' }}>
                  {m}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={onRefreshModels}
              disabled={isLoadingModels}
              title="Refresh model list"
              className="flex-shrink-0 px-2.5 py-2 rounded-lg text-sm transition-all disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
              style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--text-sidebar)' }}
              {...hoverHandlers('rgba(255,255,255,0.18)', 'rgba(255,255,255,0.1)')}
            >
              {isLoadingModels ? '⟳' : '↺'}
            </button>
          </div>

          {modelsError && (
            <p className={sidebarErrorTextClass} style={{ color: '#f87171' }}>
              {modelsError}
            </p>
          )}
        </section>

        {/* Action buttons */}
        <section className="space-y-1">
          <div className="flex items-center gap-1.5 mb-2 min-w-0">
            <p
              className={`${sidebarSectionLabelRowClass} flex-1 min-w-0 truncate`}
              style={{ color: 'rgba(255,255,255,0.45)' }}
            >
              History
            </p>
            <button
              type="button"
              onClick={onRefreshHistory}
              className="text-xs px-2 py-0.5 rounded-md transition-all flex-shrink-0"
              style={{ color: 'var(--text-sidebar)', background: 'rgba(255,255,255,0.08)' }}
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={onDeleteAllHistory}
              className="text-xs px-2 py-0.5 rounded-md transition-all flex-shrink-0"
              style={{ color: '#fca5a5', background: 'rgba(248,113,113,0.12)' }}
              title="Delete all saved conversations"
            >
              Delete All
            </button>
          </div>
          {historyError && (
            <p className={sidebarHelperMutedClass} style={{ color: '#f87171' }}>
              {historyError}
            </p>
          )}
          {isLoadingHistory && (
            <p className={sidebarHelperMutedClass} style={{ color: 'rgba(255,255,255,0.6)' }}>
              Loading history...
            </p>
          )}
          {!isLoadingHistory && historySessions.length === 0 && (
            <p className={sidebarHelperMutedClass} style={{ color: 'rgba(255,255,255,0.6)' }}>
              No saved conversations
            </p>
          )}
          {historySessions.slice(0, 20).map(item => (
            <div key={item.id} className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => onLoadHistorySession(item.id)}
                title={item.title || 'New Chat'}
                className="flex-1 min-w-0 text-left px-2.5 py-2 rounded-lg text-xs transition-all"
                style={{ color: 'var(--text-sidebar)', background: 'rgba(255,255,255,0.06)' }}
                {...hoverHandlers('rgba(255,255,255,0.12)', 'rgba(255,255,255,0.06)')}
              >
                <p className={`truncate ${sidebarStaticBaseClass}`}>{item.title || 'New Chat'}</p>
                <p
                  className={`truncate ${sidebarStaticBaseClass}`}
                  style={{ color: 'rgba(255,255,255,0.5)' }}
                >
                  {fmtDate(item.updated_at)}
                </p>
              </button>
              <button
                type="button"
                onClick={() => onDeleteHistorySession(item.id)}
                className="px-2 py-1 rounded-md text-xs"
                style={{ color: '#fca5a5', background: 'rgba(255,255,255,0.08)' }}
                title="Delete conversation"
              >
                ×
              </button>
            </div>
          ))}
        </section>

        {/* Action buttons */}
        <section className="space-y-1">
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
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
            <span className={sidebarStaticBaseClass}>Clear Chat</span>
          </button>

        </section>

        {/* File Upload */}
        <section>
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
            Analyze File
          </p>
          <FileUpload
            model={selectedModel}
            systemInstruction={systemInstruction}
            onStream={onStream}
            onFileContext={onFileContext}
            onChartSpec={event => onChartSpec(event.chart)}
          />
          {fileContext && (
            <div
              className="mt-2 text-xs px-2 py-1.5 rounded-lg flex items-center justify-between gap-2"
              style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--text-sidebar)' }}
            >
              <span className={sidebarFileChipNameClass}>{fileContext.filename}</span>
              <button
                type="button"
                onClick={onClearFileContext}
                className="px-1 rounded"
                style={{ color: '#fca5a5' }}
                title="Clear file context"
              >
                ×
              </button>
            </div>
          )}
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

        <p className={sidebarFooterAttributionClass} style={{ color: 'rgba(255,255,255,0.38)' }}>
          Powered by{' '}
          <span className={sidebarFooterHighlightClass} style={{ color: 'var(--gold)' }}>
            Mingzhi Hu
          </span>
        </p>
      </div>
    </aside>
  )
}

export default Sidebar
