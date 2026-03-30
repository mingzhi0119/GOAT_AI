import type { FC } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '../api/types'

interface Props {
  message: Message
}

/** Renders a single chat turn with role-based styling and Markdown support. */
const MessageBubble: FC<Props> = ({ message }) => {
  const isUser = message.role === 'user'

  return (
    <div className={`flex items-end gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Assistant avatar */}
      {!isUser && (
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold select-none"
          style={{ background: 'var(--navy)', color: 'var(--gold)' }}
          aria-hidden="true"
        >
          G
        </div>
      )}

      {/* Bubble */}
      <div
        className={[
          'max-w-[78%] rounded-2xl px-4 py-3',
          isUser ? 'rounded-br-sm' : 'rounded-bl-sm',
          !isUser && message.isStreaming ? 'streaming-cursor' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        style={{
          background: isUser ? 'var(--bg-user-bubble)' : 'var(--bg-asst-bubble)',
          color: isUser ? 'var(--text-user-bubble)' : 'var(--text-asst-bubble)',
        }}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="prose-msg">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content || ' '}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold select-none"
          style={{ background: 'var(--gold)', color: 'var(--navy)' }}
          aria-hidden="true"
        >
          U
        </div>
      )}
    </div>
  )
}

export default MessageBubble
