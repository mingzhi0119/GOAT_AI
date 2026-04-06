import { useState, type FC } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '../api/types'
import GoatIcon from './GoatIcon'

interface Props {
  message: Message
  /** When true, strip :::chart blocks emitted by the structured-output protocol. */
  hasFileContext?: boolean
}

/** Copy the plain text of a message to the clipboard. */
async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text)
  } else {
    // Fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
}

/**
 * Strip the :::chart JSON block the LLM emits as part of the structured-output
 * protocol.  During streaming we hide any partial block starting at :::chart;
 * after streaming the complete block (:::chart ... :::) is removed.
 */
function stripChartBlock(text: string, isStreaming: boolean): string {
  // Remove complete :::chart ... ::: blocks
  let clean = text.replace(/:::chart[\s\S]*?:::/g, '')
  // During streaming hide the incomplete tail starting at :::chart
  if (isStreaming) {
    clean = clean.replace(/:::chart[\s\S]*$/, '')
  }
  return clean.trimEnd()
}

/** Renders a single chat turn with role-based styling, Markdown, and copy button. */
const MessageBubble: FC<Props> = ({ message, hasFileContext = false }) => {
  const isUser = message.role === 'user'
  const isError = message.isError === true
  const [copied, setCopied] = useState(false)

  // Only strip :::chart blocks when a file is loaded — avoids accidentally
  // truncating responses that legitimately contain ":::chart" as text.
  const displayContent =
    isUser || !hasFileContext
      ? message.content
      : stripChartBlock(message.content, message.isStreaming ?? false)

  return (
    <div className={`flex items-end gap-2 group ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Assistant avatar — same golden goat mark as sidebar / welcome */}
      {!isUser && (
        <span className="flex-shrink-0 inline-flex" aria-label="GOAT AI">
          <GoatIcon size={28} variant="circle" />
        </span>
      )}

      {/* Bubble + copy button wrapper */}
      <div className={`flex flex-col gap-1 max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div
          className={[
            'rounded-2xl px-4 py-3 w-full',
            isUser ? 'rounded-br-sm' : 'rounded-bl-sm',
            !isUser && message.isStreaming ? 'streaming-cursor' : '',
          ]
            .filter(Boolean)
            .join(' ')}
          style={{
            background: isError
              ? 'rgba(239,68,68,0.08)'
              : isUser
                ? 'var(--bg-user-bubble)'
                : 'var(--bg-asst-bubble)',
            color: isError
              ? '#dc2626'
              : isUser
                ? 'var(--text-user-bubble)'
                : 'var(--text-asst-bubble)',
            border: isError ? '1px solid rgba(239,68,68,0.3)' : 'none',
          }}
        >
          {isError ? (
            <div className="flex items-start gap-2 text-sm">
              <span className="flex-shrink-0 mt-0.5" aria-hidden="true">⚠️</span>
              <div>
                <p className="font-medium mb-0.5">Request failed</p>
                <p className="text-xs opacity-80">{message.content}</p>
              </div>
            </div>
          ) : isUser ? (
            <p className="text-sm whitespace-pre-wrap break-words">{displayContent}</p>
          ) : (
            <div className="prose-msg">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {displayContent || ' '}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Copy button — visible on group hover, hidden while streaming */}
        {!message.isStreaming && displayContent && (
          <button
            type="button"
            onClick={() => void copyToClipboard(displayContent).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })}
            title={copied ? 'Copied!' : 'Copy message'}
            className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-0.5 rounded text-xs flex items-center gap-1"
            style={{
              color: 'var(--text-muted)',
              background: 'transparent',
            }}
          >
            {copied ? (
              <>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/>
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25v-7.5z"/>
                  <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25v-7.5zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25h-7.5z"/>
                </svg>
                Copy
              </>
            )}
          </button>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xl leading-none select-none"
          style={{ background: 'var(--navy)', color: '#ffffff' }}
          aria-hidden="true"
        >
          🧑‍💼
        </div>
      )}
    </div>
  )
}

export default MessageBubble
