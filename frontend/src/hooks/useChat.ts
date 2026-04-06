import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/chat'
import type { ChatMessage, ChatStreamEvent, ChartSpec, Message, OllamaOptionsPayload } from '../api/types'

const MESSAGES_KEY = 'goat-ai-messages'
const SESSION_KEY = 'goat-ai-session-id'
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
  sendMessage: (
    content: string,
    model: string,
    userName?: string,
    fileContextPrompt?: string,
    systemInstruction?: string,
    ollamaOptions?: OllamaOptionsPayload,
    onChartSpec?: (spec: ChartSpec) => void,
  ) => Promise<void>
  streamToChat: (gen: AsyncGenerator<string>) => Promise<void>
  clearMessages: () => void
  stopStreaming: () => void
  sessionId: string | null
  loadSession: (sessionId: string, messages: ChatMessage[]) => void
}

/** Stream a mixed token/chart-spec generator into an existing assistant message slot. */
function useStreamIntoMessage() {
  const run = useCallback(
    async (
      gen: AsyncGenerator<ChatStreamEvent>,
      msgId: string,
      setMsgs: React.Dispatch<React.SetStateAction<Message[]>>,
      setStreaming: React.Dispatch<React.SetStateAction<boolean>>,
      onChartSpec?: (spec: ChartSpec) => void,
    ) => {
      try {
        for await (const event of gen) {
          if (typeof event === 'string') {
            setMsgs(prev =>
              prev.map(m => (m.id === msgId ? { ...m, content: m.content + event } : m)),
            )
          } else {
            // ChartSpec object from chart_spec SSE event
            onChartSpec?.(event)
          }
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
  const [sessionId, setSessionId] = useState<string | null>(() => localStorage.getItem(SESSION_KEY))
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

  useEffect(() => {
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId)
    else localStorage.removeItem(SESSION_KEY)
  }, [sessionId])

  const _startStream = useCallback(
    async (
      gen: AsyncGenerator<ChatStreamEvent>,
      prependMessages?: Message[],
      onChartSpec?: (spec: ChartSpec) => void,
    ) => {
      const asstId = crypto.randomUUID()
      setMessages(prev => [
        ...(prependMessages ?? prev),
        { id: asstId, role: 'assistant', content: '', isStreaming: true },
      ])
      setIsStreaming(true)
      await _runStream(gen, asstId, setMessages, setIsStreaming, onChartSpec)
    },
    [_runStream],
  )

  const sendMessage = useCallback(
    async (
      content: string,
      model: string,
      userName?: string,
      fileContextPrompt?: string,
      systemInstruction?: string,
      ollamaOptions?: OllamaOptionsPayload,
      onChartSpec?: (spec: ChartSpec) => void,
    ) => {
      if (isStreaming) return

      const activeSessionId = sessionId ?? crypto.randomUUID()
      if (!sessionId) setSessionId(activeSessionId)

      let baseHistory: ChatMessage[] = messagesRef.current.map(m => ({
        role: m.role,
        content: m.content,
      }))
      if (
        fileContextPrompt &&
        !baseHistory.some(m => m.role === 'user' && m.content === fileContextPrompt)
      ) {
        baseHistory = [
          { role: 'user', content: fileContextPrompt },
          { role: 'assistant', content: 'I have loaded the file context.' },
          ...baseHistory,
        ]
      }
      const history: ChatMessage[] = [
        ...baseHistory,
        { role: 'user' as const, content },
      ]
      const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content }

      const ctrl = new AbortController()
      abortControllerRef.current = ctrl
      try {
        await _startStream(
          streamChat(
            {
              model,
              messages: history,
              session_id: activeSessionId,
              ...(systemInstruction?.trim()
                ? { system_instruction: systemInstruction.trim() }
                : {}),
              ...(ollamaOptions
                ? {
                    temperature: ollamaOptions.temperature,
                    max_tokens: ollamaOptions.max_tokens,
                    top_p: ollamaOptions.top_p,
                  }
                : {}),
            },
            { signal: ctrl.signal, userName },
          ),
          [...messagesRef.current, userMsg],
          onChartSpec,
        )
      } finally {
        abortControllerRef.current = null
      }
    },
    [isStreaming, sessionId, _startStream],
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
    setSessionId(null)
    localStorage.removeItem(MESSAGES_KEY)
  }, [])

  const loadSession = useCallback((nextSessionId: string, sessionMessages: ChatMessage[]) => {
    setSessionId(nextSessionId)

    // Prefixes used when injecting the file-context turn into the conversation.
    const FILE_CONTEXT_PREFIXES = [
      '[User uploaded tabular data for analysis]',
      '[User requested analysis of uploaded tabular data]',
    ]
    const FILE_CONTEXT_REPLY = 'I have loaded the file context.'

    // Cast to loose type so __chart__ sentinels (not in the ChatMessage union) pass through.
    const raw = sessionMessages as Array<{ role: string; content: string }>
    const uiRows = raw.filter(m => m.role === 'user' || m.role === 'assistant')

    const mapped: Message[] = []
    let i = 0
    while (i < uiRows.length) {
      // Explicit non-null assertion: the while-guard ensures i is in bounds.
      // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
      const m = uiRows[i]!
      const isFileCtx =
        m.role === 'user' && FILE_CONTEXT_PREFIXES.some(p => m.content.startsWith(p))

      if (isFileCtx) {
        // Keep in state (LLM needs the CSV for follow-up chart requests) but hide from UI.
        mapped.push({ id: crypto.randomUUID(), role: 'user', content: m.content, hidden: true })
        const next = uiRows[i + 1]
        if (next && next.role === 'assistant' && next.content === FILE_CONTEXT_REPLY) {
          mapped.push({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: next.content,
            hidden: true,
          })
          i += 2
        } else {
          i++
        }
      } else {
        mapped.push({
          id: crypto.randomUUID(),
          role: m.role as Message['role'],
          content: m.content,
        })
        i++
      }
    }

    setMessages(mapped)
  }, [])

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
  }, [])

  return {
    messages,
    isStreaming,
    sendMessage,
    streamToChat,
    clearMessages,
    stopStreaming,
    sessionId,
    loadSession,
  }
}
