import { useCallback, useRef, useState } from 'react'
import { streamChat } from '../api/chat'
import type { ChatMessage, Message } from '../api/types'

export interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  sendMessage: (content: string, model: string) => Promise<void>
  streamToChat: (gen: AsyncGenerator<string>) => Promise<void>
  clearMessages: () => void
}

/** Stream a generator's tokens into an existing assistant message slot. */
function useStreamIntoMessage() {
  const setMessagesRef = useRef<React.Dispatch<React.SetStateAction<Message[]>> | null>(null)
  const setStreamingRef = useRef<React.Dispatch<React.SetStateAction<boolean>> | null>(null)

  const run = useCallback(
    async (
      gen: AsyncGenerator<string>,
      msgId: string,
      setMsgs: React.Dispatch<React.SetStateAction<Message[]>>,
      setStreaming: React.Dispatch<React.SetStateAction<boolean>>,
    ) => {
      setMessagesRef.current = setMsgs
      setStreamingRef.current = setStreaming
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

/** Manages conversation state and SSE streaming for chat and uploads. */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  // Ref lets sendMessage read the current messages without them in useCallback deps.
  const messagesRef = useRef<Message[]>([])
  messagesRef.current = messages

  const _runStream = useStreamIntoMessage()

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
    async (content: string, model: string) => {
      if (isStreaming) return

      const history: ChatMessage[] = [
        ...messagesRef.current.map(m => ({ role: m.role, content: m.content })),
        { role: 'user' as const, content },
      ]
      const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content }

      await _startStream(
        streamChat({ model, messages: history }),
        [...messagesRef.current, userMsg],
      )
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

  const clearMessages = useCallback(() => setMessages([]), [])

  return { messages, isStreaming, sendMessage, streamToChat, clearMessages }
}
