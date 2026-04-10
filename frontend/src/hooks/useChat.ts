import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/chat'
import type { HistorySessionDetail } from '../api/history'
import type {
  ChatMessage,
  ChatStreamEvent,
  ChartSpec,
  Message,
  OllamaOptionsPayload,
} from '../api/types'
import { hydrateHistorySession } from '../utils/sessionHistory'

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
    knowledgeDocumentIds?: string[],
    systemInstruction?: string,
    ollamaOptions?: OllamaOptionsPayload,
    onChartSpec?: (spec: ChartSpec) => void,
    imageAttachmentIds?: string[],
  ) => Promise<void>
  streamToChat: (gen: AsyncGenerator<ChatStreamEvent>) => Promise<void>
  clearMessages: () => void
  stopStreaming: () => void
  sessionId: string | null
  loadSession: (session: HistorySessionDetail) => void
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
          if (event.type === 'token') {
            setMsgs(prev =>
              prev.map(m => (m.id === msgId ? { ...m, content: m.content + event.token } : m)),
            )
          } else if (event.type === 'thinking') {
            setMsgs(prev =>
              prev.map(m =>
                m.id === msgId
                  ? {
                      ...m,
                      thinkingContent: (m.thinkingContent ?? '') + event.token,
                    }
                  : m,
              ),
            )
          } else if (event.type === 'artifact') {
            const { type: _type, ...artifact } = event
            setMsgs(prev =>
              prev.map(m =>
                m.id === msgId
                  ? { ...m, artifacts: [...(m.artifacts ?? []), artifact] }
                  : m,
              ),
            )
          } else if (event.type === 'chart_spec') {
            onChartSpec?.(event.chart)
          } else if (event.type === 'error') {
            setMsgs(prev =>
              prev.map(m =>
                m.id === msgId ? { ...m, content: event.message, isError: true } : m,
              ),
            )
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
        { id: asstId, role: 'assistant', content: '', isStreaming: true, artifacts: [] },
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
      knowledgeDocumentIds?: string[],
      systemInstruction?: string,
      ollamaOptions?: OllamaOptionsPayload,
      onChartSpec?: (spec: ChartSpec) => void,
      imageAttachmentIds?: string[],
    ) => {
      if (isStreaming) return

      const activeSessionId = sessionId ?? crypto.randomUUID()
      if (!sessionId) setSessionId(activeSessionId)

      const userText =
        content.trim() ||
        (imageAttachmentIds && imageAttachmentIds.length > 0
          ? 'What do you see in this image?'
          : '')

      let baseHistory: ChatMessage[] = messagesRef.current.map(m => ({
        role: m.role,
        content: m.content,
        ...(m.file_context ? { file_context: true as const } : {}),
      }))
      const history: ChatMessage[] = [
        ...baseHistory,
        { role: 'user' as const, content: userText },
      ]
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: userText,
        ...(imageAttachmentIds && imageAttachmentIds.length > 0
          ? { image_attachment_ids: imageAttachmentIds }
          : {}),
      }

      const ctrl = new AbortController()
      abortControllerRef.current = ctrl
      try {
        await _startStream(
          streamChat(
            {
              model,
              messages: history,
              ...(knowledgeDocumentIds && knowledgeDocumentIds.length > 0
                ? { knowledge_document_ids: knowledgeDocumentIds }
                : {}),
              ...(imageAttachmentIds && imageAttachmentIds.length > 0
                ? { image_attachment_ids: imageAttachmentIds }
                : {}),
              session_id: activeSessionId,
              ...(systemInstruction?.trim()
                ? { system_instruction: systemInstruction.trim() }
                : {}),
              ...(ollamaOptions
                ? {
                    temperature: ollamaOptions.temperature,
                    max_tokens: ollamaOptions.max_tokens,
                    top_p: ollamaOptions.top_p,
                    ...(typeof ollamaOptions.think === 'boolean'
                      ? { think: ollamaOptions.think }
                      : {}),
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
    async (gen: AsyncGenerator<ChatStreamEvent>) => {
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

  const loadSession = useCallback((session: HistorySessionDetail) => {
    setSessionId(session.id)
    setMessages(hydrateHistorySession(session))
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
