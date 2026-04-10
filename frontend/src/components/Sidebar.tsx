import { type FC, type MouseEvent } from 'react'
import type { HistorySessionItem } from '../api/history'
import type { ChatLayoutMode } from '../utils/chatLayout'
import GoatIcon from './GoatIcon'
import {
  sidebarFooterAttributionClass,
  sidebarFooterHighlightClass,
  sidebarHelperMutedClass,
  sidebarSectionLabelClass,
  sidebarSectionLabelRowClass,
  sidebarStaticBaseClass,
} from './sidebarStaticText'

interface Props {
  onClearChat: () => void
  userName: string
  onUserNameChange: (name: string) => void
  layoutMode?: ChatLayoutMode
  open?: boolean
  onClose?: () => void
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

const NewChatIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 3.25v9.5M3.25 8h9.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
)

const Sidebar: FC<Props> = ({
  onClearChat,
  userName: _userName,
  onUserNameChange: _onUserNameChange,
  layoutMode = 'wide',
  open = true,
  onClose,
  historySessions,
  isLoadingHistory,
  historyError,
  onLoadHistorySession,
  onDeleteHistorySession,
  onRefreshHistory,
  onDeleteAllHistory,
}) => {
  const isNarrow = layoutMode === 'narrow'
  const isOpen = isNarrow ? open : true

  const closeOverlay = () => {
    if (isNarrow) onClose?.()
  }

  return (
    <aside
      className={[
        'flex min-h-0 flex-col overflow-x-hidden transition-transform duration-200 ease-out',
        isNarrow
          ? 'fixed inset-y-0 left-0 z-40 h-[100dvh] w-[min(16rem,calc(100vw-1.25rem))] max-w-[16rem] shadow-[0_20px_48px_rgba(15,23,42,0.16)]'
          : 'h-screen w-64 flex-shrink-0',
        isNarrow && !isOpen ? '-translate-x-full' : 'translate-x-0',
      ].join(' ')}
      style={{ background: 'var(--bg-sidebar)' }}
      aria-hidden={isNarrow ? !isOpen : undefined}
    >
      <div className="flex h-12 flex-shrink-0 items-center justify-between gap-2.5 px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <GoatIcon size={28} />
          <h1
            className="cursor-default select-none text-[15px] font-semibold leading-none tracking-[-0.02em]"
            style={{ color: 'var(--text-sidebar)' }}
          >
            GOAT AI
          </h1>
        </div>
        {isNarrow && (
          <button
            type="button"
            onClick={closeOverlay}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm"
            style={{ color: 'var(--sidebar-muted)' }}
            aria-label="Close sidebar"
          >
            x
          </button>
        )}
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
        <section className="space-y-1">
          <p className={sidebarSectionLabelClass} style={{ color: 'var(--sidebar-muted)' }}>
            Actions
          </p>

          <button
            type="button"
            onClick={() => {
              onClearChat()
              closeOverlay()
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-all"
            style={{ color: 'var(--text-sidebar)', background: 'transparent' }}
            {...hoverHandlers('var(--sidebar-hover)')}
          >
            <span className="flex w-4 flex-shrink-0 items-center justify-center">
              <NewChatIcon />
            </span>
            <span className={sidebarStaticBaseClass}>New Chat</span>
          </button>
        </section>

        <section className="space-y-1">
          <div className="mb-2 flex min-w-0 items-center gap-1.5">
            <p
              className={`${sidebarSectionLabelRowClass} min-w-0 flex-1 truncate`}
              style={{ color: 'var(--sidebar-muted)' }}
            >
              History
            </p>
            <button
              type="button"
              onClick={onRefreshHistory}
              className="flex-shrink-0 rounded-md px-2 py-0.5 text-xs transition-all"
              style={{ color: 'var(--text-sidebar)', background: 'var(--sidebar-surface)' }}
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={onDeleteAllHistory}
              className="flex-shrink-0 rounded-md px-2 py-0.5 text-xs transition-all"
              style={{ color: 'var(--sidebar-danger)', background: 'var(--sidebar-danger-bg)' }}
              title="Delete all saved conversations"
            >
              Delete All
            </button>
          </div>

          {historyError && (
            <p className={sidebarHelperMutedClass} style={{ color: 'var(--sidebar-danger)' }}>
              {historyError}
            </p>
          )}
          {isLoadingHistory && (
            <p className={sidebarHelperMutedClass} style={{ color: 'var(--sidebar-muted)' }}>
              Loading history...
            </p>
          )}
          {!isLoadingHistory && historySessions.length === 0 && (
            <p className={sidebarHelperMutedClass} style={{ color: 'var(--sidebar-muted)' }}>
              No saved conversations
            </p>
          )}
          {historySessions.slice(0, 20).map(item => (
            <div key={item.id} className="group/history flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  onLoadHistorySession(item.id)
                  closeOverlay()
                }}
                title={item.title || 'New Chat'}
                className="min-w-0 flex-1 rounded-lg px-2.5 py-2 text-left text-xs transition-all"
                style={{ color: 'var(--text-sidebar)', background: 'var(--sidebar-surface-muted)' }}
                {...hoverHandlers('var(--sidebar-hover)', 'var(--sidebar-surface-muted)')}
              >
                <p className={`truncate ${sidebarStaticBaseClass}`}>{item.title || 'New Chat'}</p>
              </button>
              <button
                type="button"
                onClick={() => onDeleteHistorySession(item.id)}
                className="rounded-md px-2 py-1 text-xs opacity-0 transition-opacity group-hover/history:opacity-100 focus-visible:opacity-100"
                style={{ color: 'var(--sidebar-danger)', background: 'var(--sidebar-surface)' }}
                title="Delete conversation"
              >
                x
              </button>
            </div>
          ))}
        </section>
      </div>

      <div className="flex-shrink-0 space-y-3 px-5 py-4">
        <img
          src="./simon_logo.svg"
          alt="Simon Business School - University of Rochester"
          className="simon-footer-logo w-full max-w-[148px]"
          style={{
            opacity: 0.85,
          }}
        />

        <p className={sidebarFooterAttributionClass} style={{ color: 'var(--sidebar-muted)' }}>
          Powered by{' '}
          <a
            href="https://mingzhi0119.github.io/"
            target="_blank"
            rel="noopener noreferrer"
            title="Open homepage (new tab)"
            className={`${sidebarFooterHighlightClass} cursor-pointer`}
            style={{ color: 'var(--text-sidebar)' }}
          >
            Mingzhi Hu
          </a>
        </p>
      </div>
    </aside>
  )
}

export default Sidebar
