import { useEffect, useRef, useState, type FC, type KeyboardEvent } from 'react'
import type { Message } from '../api/types'
import MessageBubble from './MessageBubble'

const STARTER_PROMPTS = [
  'Summarize key trends in consumer behavior',
  'What are the top strategic risks for 2026?',
  'Explain Porter\'s Five Forces briefly',
  'Draft an executive summary template',
]

interface Props {
  messages: Message[]
  isStreaming: boolean
  selectedModel: string
  onSendMessage: (content: string) => void
}

/** Main chat panel: message list + auto-scroll + input area. */
const ChatWindow: FC<Props> = ({ messages, isStreaming, selectedModel, onSendMessage }) => {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    onSendMessage(trimmed)
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-grow up to 180 px
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`
  }

  const canSend = input.trim().length > 0 && !isStreaming

  return (
    <div
      className="flex flex-col flex-1 min-w-0 h-screen"
      style={{ background: 'var(--bg-chat)' }}
    >
      {/* ── Messages area ─────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-4">
            <div
              className="w-20 h-20 rounded-2xl overflow-hidden"
              style={{
                border: '1.5px solid #FFCD00',
                background: '#2b2b2b',
              }}
            >
              <img
                src="./golden_goat_icon.png"
                alt="GOAT AI"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
            <div>
              <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--text-main)' }}>
                Welcome to GOAT AI
              </h2>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Strategic Intelligence — Simon Business School
              </p>
              {selectedModel && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Model: <span style={{ color: 'var(--gold)' }}>{selectedModel}</span>
                </p>
              )}
            </div>
            {/* Starter prompts */}
            <div className="grid grid-cols-2 gap-2 w-full max-w-md mt-2">
              {STARTER_PROMPTS.map(prompt => (
                <button
                  key={prompt}
                  onClick={() => onSendMessage(prompt)}
                  className="text-xs px-3 py-2 rounded-xl text-left transition-colors hover:opacity-80"
                  style={{
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-main)',
                    background: 'var(--bg-asst-bubble)',
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input area ────────────────────────────────────────────── */}
      <div
        className="flex-shrink-0 px-4 py-3 border-t"
        style={{ borderColor: 'var(--border-color)', background: 'var(--bg-chat)' }}
      >
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Message GOAT AI… (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 transition-all"
            style={{
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              color: 'var(--text-main)',
              lineHeight: '1.5',
              maxHeight: '180px',
              // focus ring color via CSS variable isn't easily set in inline style;
              // Tailwind focus:ring-blue-500 handles it
            }}
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSend}
            className="flex-shrink-0 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-40"
            style={{
              background: canSend ? 'var(--navy)' : 'var(--border-color)',
              color: canSend ? '#fff' : 'var(--text-muted)',
            }}
          >
            {isStreaming ? (
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--gold)' }} />
                …
              </span>
            ) : (
              'Send'
            )}
          </button>
        </div>
        <p className="text-center text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
          AI may make mistakes. Verify important information.
        </p>
      </div>
    </div>
  )
}

export default ChatWindow
