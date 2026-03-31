import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/chat'
import type { ChatMessage, Message } from '../api/types'

const MESSAGES_KEY = 'goat-ai-messages'
const MAX_STORED = 100

function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(MESSAGES_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return (parsed as Message[]).filter(m => !m.isStreaming)
  } catch {
    return []
  }
}

export interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  sendMessage: (content: string, model: string, userName?: string) => Promise<void>
  streamToChat: (gen: AsyncGenerator<string>) => Promise<void>
  clearMessages: () => void
  stopStreaming: () => void
}

/** Stream a generator's tokens into an existing assistant message slot. */
function useStreamIntoMessage() {
  const run = useCallback(
    async (
      gen: AsyncGenerator<string>,
      msgId: string,
      setMsgs: React.Dispatch<React.SetStateAction<Message[]>>,
      setStreaming: React.Dispatch<React.SetStateAction<boolean>>,
    ) => {
      try {
        for await (const token of gen) {
          setMsgs(prev =>
            prev.map(m => (m.id === msgId ? { ...m, content: m.content + token } : m)),
          )
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Streaming error'
        setMsgs(prev =>
          prev.map(m =>
            m.id === msgId ? { ...m, content: msg, isError: true } : m,
          ),
        )
      } finally {
        setMsgs(prev =>
          prev.map(m => (m.id === msgId ? { ...m, isStreaming: false } : m)),
        )
        setStreaming(false)
      }
    },
    [],
  )
  return run
}

/**
 * Manages conversation state, SSE streaming, abort control, and local persistence.
 *
 * Session persistence: messages are saved to localStorage on every change (up to
 * MAX_STORED non-streaming messages) and restored on page load.
 *
 * Abort: call stopStreaming() to cancel a live stream; the partial response is kept.
 */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>(loadMessages)
  const [isStreaming, setIsStreaming] = useState(false)

  const messagesRef = useRef<Message[]>([])
  messagesRef.current = messages

  const abortControllerRef = useRef<AbortController | null>(null)
  const _runStream = useStreamIntoMessage()

  // Persist completed messages to localStorage on every change
  useEffect(() => {
    try {
      const toStore = messages.filter(m => !m.isStreaming).slice(-MAX_STORED)
      localStorage.setItem(MESSAGES_KEY, JSON.stringify(toStore))
    } catch {
      // localStorage might be full or unavailable
    }
  }, [messages])

  const _startStream = useCallback(
    async (gen: AsyncGenerator<string>, prependMessages?: Message[]) => {
      const asstId = crypto.randomUUID()
      setMessages(prev => [
        ...(prependMessages ?? prev),
        { id: asstId, role: 'assistant', content: '', isStreaming: true },
      ])
      setIsStreaming(true)
      await _runStream(gen, asstId, setMessages, setIsStreaming)
    },
    [_runStream],
  )

  const sendMessage = useCallback(
    async (content: string, model: string, userName?: string) => {
      if (isStreaming) return

      const history: ChatMessage[] = [
        ...messagesRef.current.map(m => ({ role: m.role, content: m.content })),
        { role: 'user' as const, content },
      ]
      const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content }

      const ctrl = new AbortController()
      abortControllerRef.current = ctrl
      try {
        await _startStream(
          streamChat({ model, messages: history }, { signal: ctrl.signal, userName }),
          [...messagesRef.current, userMsg],
        )
      } finally {
        abortControllerRef.current = null
      }
    },
    [isStreaming, _startStream],
  )

  const streamToChat = useCallback(
    async (gen: AsyncGenerator<string>) => {
      if (isStreaming) return
      await _startStream(gen)
    },
    [isStreaming, _startStream],
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    localStorage.removeItem(MESSAGES_KEY)
  }, [])

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
  }, [])

  return { messages, isStreaming, sendMessage, streamToChat, clearMessages, stopStreaming }
}
