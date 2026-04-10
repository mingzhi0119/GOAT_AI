import { useState, type CSSProperties, type FC } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatArtifact, Message } from '../api/types'
import type { ChatLayoutMode } from '../utils/chatLayout'

interface Props {
  message: Message
  /** When true, strip :::chart blocks emitted by the structured-output protocol. */
  hasFileContext?: boolean
  layoutMode?: ChatLayoutMode
}

async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text)
  } else {
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

function stripChartBlock(text: string, isStreaming: boolean): string {
  let clean = text.replace(/:::chart[\s\S]*?:::/g, '')
  if (isStreaming) {
    clean = clean.replace(/:::chart[\s\S]*$/, '')
  }
  return clean.trimEnd()
}

function resolveArtifactLink(
  href: string,
  artifactByFilename: Map<string, ChatArtifact>,
): ChatArtifact | null {
  if (!href) return null
  if (
    /^[a-z]+:/i.test(href) ||
    href.startsWith('/') ||
    href.startsWith('./') ||
    href.startsWith('../')
  ) {
    return null
  }
  return artifactByFilename.get(href) ?? null
}

function formatArtifactSize(byteSize: number): string {
  if (byteSize < 1024) return `${byteSize} B`
  if (byteSize < 1024 * 1024) return `${(byteSize / 1024).toFixed(1)} KB`
  return `${(byteSize / (1024 * 1024)).toFixed(1)} MB`
}

const MessageBubble: FC<Props> = ({ message, hasFileContext = false, layoutMode = 'wide' }) => {
  const isUser = message.role === 'user'
  const isError = message.isError === true
  const isNarrow = layoutMode === 'narrow'
  const [copied, setCopied] = useState(false)
  const artifactByFilename = new Map(
    (message.artifacts ?? []).map(artifact => [artifact.filename, artifact]),
  )

  const displayContent =
    isUser || !hasFileContext
      ? message.content
      : stripChartBlock(message.content, message.isStreaming ?? false)

  const copyControl = (className: string, buttonStyle?: CSSProperties) => (
    <button
      type="button"
      onClick={() =>
        void copyToClipboard(displayContent).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 2000)
        })
      }
      title={copied ? 'Copied!' : 'Copy message'}
      className={className}
      style={
        buttonStyle ?? {
          color: 'var(--text-muted)',
          background: 'transparent',
        }
      }
    >
      {copied ? (
        <>
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
          </svg>
          Copied
        </>
      ) : (
        <>
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25v-7.5z" />
            <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25v-7.5zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25h-7.5z" />
          </svg>
          Copy
        </>
      )}
    </button>
  )

  return (
    <div className={`ui-static flex group ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={
          isUser
            ? `flex ${isNarrow ? 'max-w-[94%]' : 'max-w-[78%]'} flex-col gap-1 items-end`
            : `flex w-full ${isNarrow ? 'max-w-[94%]' : 'max-w-[78%]'} flex-col gap-1 items-stretch min-w-0`
        }
      >
        {isError ? (
          <div
            className="w-full min-w-0 rounded-[18px] px-4 py-3"
            style={{
              background: 'var(--composer-danger-bg)',
              color: 'var(--composer-danger-text)',
              border: '1px solid var(--composer-danger-border)',
            }}
          >
            <div className="flex items-start gap-2 text-sm">
              <span className="mt-0.5 flex-shrink-0" aria-hidden="true">
                !
              </span>
              <div>
                <p className="mb-0.5 font-medium">Request failed</p>
                <p className="text-xs opacity-80">{message.content}</p>
              </div>
            </div>
          </div>
        ) : isUser ? (
          <div
            className={[
              'w-full min-w-0 rounded-[18px] px-4 py-3',
              message.isStreaming ? 'streaming-cursor' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            style={{
              background: 'var(--bg-user-bubble)',
              color: 'var(--text-user-bubble)',
            }}
          >
            <p className="whitespace-pre-wrap break-words text-sm">{displayContent}</p>
            {message.image_attachment_ids && message.image_attachment_ids.length > 0 && (
              <p className="mt-1.5 text-[10px] opacity-75" aria-label="Image attachments">
                {message.image_attachment_ids.length} image
                {message.image_attachment_ids.length > 1 ? 's' : ''} attached
              </p>
            )}
          </div>
        ) : (
          <div className="assistant-document-card w-full min-w-0 rounded-lg px-1 py-2 sm:px-2">
            <div className="mb-2 flex min-h-[1.25rem] flex-wrap items-center justify-end gap-2">
              {message.isStreaming && (
                <span className="mr-auto text-[10px] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Writing...
                </span>
              )}
              {!message.isStreaming && displayContent && (
                <div className="flex shrink-0 items-center">
                  {copyControl('assistant-copy-hit flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs', {
                    background: 'transparent',
                  })}
                </div>
              )}
            </div>

            {message.thinkingContent && message.thinkingContent.trim().length > 0 && (
              <details
                className="thinking-disclosure mb-3 w-full min-w-0 rounded-lg border px-3 py-2 text-left text-xs"
                aria-label="Thinking"
                style={{
                  borderColor: 'var(--border-color)',
                  background: 'var(--composer-muted-surface)',
                }}
              >
                <summary
                  className="flex w-full min-w-0 cursor-pointer list-none items-center gap-1.5 font-medium outline-none [&::-webkit-details-marker]:hidden"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <svg
                    className="thinking-chevron h-3.5 w-3.5 shrink-0 transition-transform duration-200"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    aria-hidden
                  >
                    <path d="M6.22 3.22a.75.75 0 011.06 0l4.25 4.25a.75.75 0 010 1.06L7.28 12.78a.75.75 0 01-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 010-1.06z" />
                  </svg>
                  <span>Thinking</span>
                </summary>
                <div
                  className="mt-2 max-h-80 w-full min-w-0 overflow-y-auto whitespace-pre-wrap break-words border-t pt-2 text-[13px] leading-relaxed"
                  style={{
                    borderColor: 'var(--border-color)',
                    color: 'var(--text-main)',
                  }}
                >
                  {message.thinkingContent}
                </div>
              </details>
            )}

            <div
              className={[
                'prose-msg min-w-0 w-full',
                message.isStreaming ? 'streaming-cursor' : '',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ href, children }) => {
                    const artifact = resolveArtifactLink(
                      typeof href === 'string' ? href : '',
                      artifactByFilename,
                    )
                    if (artifact) {
                      return (
                        <a href={artifact.download_url} download={artifact.filename}>
                          {children}
                        </a>
                      )
                    }
                    return <a href={href}>{children}</a>
                  },
                }}
              >
                {displayContent || ' '}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {!message.isStreaming && message.artifacts && message.artifacts.length > 0 && (
          <div className="ui-static flex flex-wrap gap-2">
            {message.artifacts.map(artifact => (
              <a
                key={artifact.artifact_id}
                href={artifact.download_url}
                download={artifact.filename}
                className="inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs transition-opacity hover:opacity-85"
                style={{
                  borderColor: 'var(--border-color)',
                  background: 'var(--composer-muted-surface)',
                  color: 'var(--text-main)',
                }}
              >
                <span className="font-medium">{artifact.label ?? artifact.filename}</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {formatArtifactSize(artifact.byte_size)}
                </span>
              </a>
            ))}
          </div>
        )}

        {!message.isStreaming && displayContent && isUser &&
          copyControl(
            'flex items-center gap-1 rounded px-2 py-0.5 text-xs opacity-0 transition-opacity group-hover:opacity-100',
          )}
      </div>
    </div>
  )
}

export default MessageBubble
