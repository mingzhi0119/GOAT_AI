import { type FC, type MouseEvent } from 'react'
import GoatIcon from './GoatIcon'
import type { HistorySessionItem } from '../api/history'
import type { ModelCapabilitiesResponse } from '../api/types'
import {
  sidebarErrorTextClass,
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
  isLoadingModelCapabilities: boolean
  modelsError: string | null
  modelCapabilities: ModelCapabilitiesResponse | null
  modelCapabilitiesError: string | null
  userName: string
  onUserNameChange: (name: string) => void
  historySessions: HistorySessionItem[]
  isLoadingHistory: boolean
  historyError: string | null
  onLoadHistorySession: (sessionId: string) => void
  onDeleteHistorySession: (sessionId: string) => void
  onRefreshHistory: () => void
  onDeleteAllHistory: () => void
}

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

const TrashIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
    <path
      fillRule="evenodd"
      d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"
    />
  </svg>
)

const Sidebar: FC<Props> = ({
  models,
  selectedModel,
  onModelChange,
  onRefreshModels,
  onClearChat,
  isLoadingModels,
  isLoadingModelCapabilities,
  modelsError,
  modelCapabilities,
  modelCapabilitiesError,
  userName,
  onUserNameChange,
  historySessions,
  isLoadingHistory,
  historyError,
  onLoadHistorySession,
  onDeleteHistorySession,
  onRefreshHistory,
  onDeleteAllHistory,
}) => {
  const fmtDate = (value: string) => {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleString()
  }

  return (
    <aside
      className="flex h-screen w-64 flex-shrink-0 min-h-0 flex-col overflow-x-hidden"
      style={{ background: 'var(--bg-sidebar)' }}
    >
      <div
        className="flex h-12 flex-shrink-0 items-center gap-2.5 border-b px-4"
        style={{ borderColor: 'rgba(255,255,255,0.1)' }}
      >
        <GoatIcon size={28} />
        <h1
          className="cursor-default select-none text-base font-extrabold leading-none"
          style={{ color: 'var(--gold)' }}
        >
          GOAT AI
        </h1>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
        <section>
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
            Your Name
          </p>
          <input
            type="text"
            value={userName}
            onChange={e => onUserNameChange(e.target.value)}
            placeholder="Optional - AI will address you"
            maxLength={40}
            className="w-full rounded-lg px-2.5 py-2 text-xs focus:outline-none"
            style={{
              background: 'rgba(255,255,255,0.1)',
              color: 'var(--text-sidebar)',
              border: '1px solid rgba(255,255,255,0.18)',
            }}
          />
        </section>

        <section>
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
            Model
          </p>
          <div className="flex min-w-0 gap-1.5">
            <select
              value={selectedModel}
              onChange={e => onModelChange(e.target.value)}
              disabled={isLoadingModels || models.length === 0}
              className="min-w-0 flex-1 cursor-pointer truncate rounded-lg px-2.5 py-2 text-xs focus:outline-none"
              style={{
                background: 'rgba(255,255,255,0.1)',
                color: 'var(--text-sidebar)',
                border: '1px solid rgba(255,255,255,0.18)',
              }}
              aria-label="Select AI model"
            >
              {isLoadingModels && <option>Loading...</option>}
              {!isLoadingModels && models.length === 0 && !modelsError && (
                <option>No models found</option>
              )}
              {models.map(model => (
                <option
                  key={model}
                  value={model}
                  style={{ background: '#001e3c', cursor: 'default' }}
                >
                  {model}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={onRefreshModels}
              disabled={isLoadingModels}
              title="Refresh model list"
              className="flex-shrink-0 rounded-lg px-2.5 py-2 text-sm transition-all disabled:cursor-not-allowed disabled:opacity-40"
              style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--text-sidebar)' }}
              {...hoverHandlers('rgba(255,255,255,0.18)', 'rgba(255,255,255,0.1)')}
            >
              {isLoadingModels ? '...' : '->'}
            </button>
          </div>

          {modelsError && (
            <p className={sidebarErrorTextClass} style={{ color: '#f87171' }}>
              {modelsError}
            </p>
          )}
          {!modelsError && selectedModel && (
            <p className={sidebarHelperMutedClass} style={{ color: 'rgba(255,255,255,0.68)' }}>
              {isLoadingModelCapabilities
                ? 'Checking chart support...'
                : modelCapabilitiesError
                  ? 'Chart support unavailable'
                  : modelCapabilities?.supports_chart_tools
                    ? 'Chart tools supported'
                    : 'Chart tools not supported'}
            </p>
          )}
        </section>

        <section className="space-y-1">
          <p className={sidebarSectionLabelClass} style={{ color: 'rgba(255,255,255,0.45)' }}>
            Actions
          </p>

          <button
            type="button"
            onClick={onClearChat}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-all"
            style={{ color: 'var(--text-sidebar)', background: 'transparent' }}
            {...hoverHandlers('var(--sidebar-hover)')}
          >
            <span className="flex w-4 flex-shrink-0 items-center justify-center">
              <TrashIcon />
            </span>
            <span className={sidebarStaticBaseClass}>Clear Chat</span>
          </button>
        </section>

        <section className="space-y-1">
          <div className="mb-2 flex min-w-0 items-center gap-1.5">
            <p
              className={`${sidebarSectionLabelRowClass} min-w-0 flex-1 truncate`}
              style={{ color: 'rgba(255,255,255,0.45)' }}
            >
              History
            </p>
            <button
              type="button"
              onClick={onRefreshHistory}
              className="flex-shrink-0 rounded-md px-2 py-0.5 text-xs transition-all"
              style={{ color: 'var(--text-sidebar)', background: 'rgba(255,255,255,0.08)' }}
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={onDeleteAllHistory}
              className="flex-shrink-0 rounded-md px-2 py-0.5 text-xs transition-all"
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
                className="min-w-0 flex-1 rounded-lg px-2.5 py-2 text-left text-xs transition-all"
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
                className="rounded-md px-2 py-1 text-xs"
                style={{ color: '#fca5a5', background: 'rgba(255,255,255,0.08)' }}
                title="Delete conversation"
              >
                x
              </button>
            </div>
          ))}
        </section>
      </div>

      <div
        className="flex-shrink-0 space-y-3 px-5 py-4"
        style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}
      >
        <img
          src="./simon_logo.svg"
          alt="Simon Business School - University of Rochester"
          className="w-full max-w-[148px]"
          style={{
            filter: 'brightness(0) invert(1)',
            opacity: 0.55,
          }}
        />

        <p className={sidebarFooterAttributionClass} style={{ color: 'rgba(255,255,255,0.38)' }}>
          Powered by{' '}
          <a
            href="https://mingzhi0119.github.io/"
            target="_blank"
            rel="noopener noreferrer"
            title="Open homepage (new tab)"
            className={`${sidebarFooterHighlightClass} cursor-pointer`}
            style={{ color: 'var(--gold)' }}
          >
            Mingzhi Hu
          </a>
        </p>
      </div>
    </aside>
  )
}

export default Sidebar
