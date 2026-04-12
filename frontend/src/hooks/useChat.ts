import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { streamChat } from '../api/chat'
import type { HistorySessionDetail } from '../api/history'
import type {
  ChatStreamEvent,
  ChartSpec,
  Message,
  OllamaOptionsPayload,
  ThemeStyle,
} from '../api/types'
import { hydrateHistorySession } from '../utils/sessionHistory'
import {
  clearStoredChatState,
  loadStoredMessages,
  loadStoredSessionId,
  persistMessages,
  persistSessionId,
} from './chatLocalPersistence'
import {
  applyStreamEvent,
  buildHistoryMessages,
  buildUserMessage,
  buildUserText,
  createAssistantStreamingMessage,
  finalizeStreamingMessage,
  markStreamError,
} from './chatStreamState'

function shouldShowThinking(think: OllamaOptionsPayload['think'] | undefined): boolean {
  return think === true || typeof think === 'string'
}

export interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  sendMessage: (
    content: string,
    model: string,
    userName?: string,
    knowledgeDocumentIds?: string[],
    planModeEnabled?: boolean,
    systemInstruction?: string,
    themeStyle?: ThemeStyle,
    ollamaOptions?: OllamaOptionsPayload,
    onChartSpec?: (spec: ChartSpec) => void,
    imageAttachmentIds?: string[],
    sessionIdOverride?: string,
  ) => Promise<string | undefined>
  streamToChat: (gen: AsyncGenerator<ChatStreamEvent>) => Promise<void>
  clearMessages: () => void
  stopStreaming: () => void
  sessionId: string | null
  loadSession: (session: HistorySessionDetail) => void
}

/** Stream a mixed token/chart-spec generator into an existing assistant message slot. */
function useStreamIntoMessage() {
  return useCallback(
    async (
      gen: AsyncGenerator<ChatStreamEvent>,
      msgId: string,
      setMessages: Dispatch<SetStateAction<Message[]>>,
      setStreaming: Dispatch<SetStateAction<boolean>>,
      onChartSpec?: (spec: ChartSpec) => void,
    ) => {
      try {
        for await (const event of gen) {
          setMessages(previous => applyStreamEvent(previous, msgId, event, onChartSpec))
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Streaming error'
        setMessages(previous => markStreamError(previous, msgId, message))
      } finally {
        setMessages(previous => finalizeStreamingMessage(previous, msgId))
        setStreaming(false)
      }
    },
    [],
  )
}

/**
 * Manages conversation state, SSE streaming, abort control, and local persistence.
 *
 * Session persistence: messages are saved to localStorage on every change and restored on page
 * load. Abort: call stopStreaming() to cancel a live stream; the partial response is kept.
 */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>(loadStoredMessages)
  const [sessionId, setSessionId] = useState<string | null>(loadStoredSessionId)
  const [isStreaming, setIsStreaming] = useState(false)

  const messagesRef = useRef<Message[]>([])
  messagesRef.current = messages

  const abortControllerRef = useRef<AbortController | null>(null)
  const runStreamIntoMessage = useStreamIntoMessage()

  useEffect(() => {
    persistMessages(messages)
  }, [messages])

  useEffect(() => {
    persistSessionId(sessionId)
  }, [sessionId])

  const startStream = useCallback(
    async (
      gen: AsyncGenerator<ChatStreamEvent>,
      prependMessages?: Message[],
      onChartSpec?: (spec: ChartSpec) => void,
      showThinking?: boolean,
    ) => {
      const assistantMessage = createAssistantStreamingMessage(showThinking)
      setMessages(previous => [...(prependMessages ?? previous), assistantMessage])
      setIsStreaming(true)
      await runStreamIntoMessage(gen, assistantMessage.id, setMessages, setIsStreaming, onChartSpec)
    },
    [runStreamIntoMessage],
  )

  const sendMessage = useCallback(
    async (
      content: string,
      model: string,
      userName?: string,
      knowledgeDocumentIds?: string[],
      planModeEnabled?: boolean,
      systemInstruction?: string,
      themeStyle?: ThemeStyle,
      ollamaOptions?: OllamaOptionsPayload,
      onChartSpec?: (spec: ChartSpec) => void,
      imageAttachmentIds?: string[],
      sessionIdOverride?: string,
    ) => {
      if (isStreaming) return undefined

      const activeSessionId = sessionIdOverride ?? sessionId ?? crypto.randomUUID()
      if (!sessionId) setSessionId(activeSessionId)

      const userText = buildUserText(content, imageAttachmentIds)
      const userMessage = buildUserMessage(userText, imageAttachmentIds)
      const history = [
        ...buildHistoryMessages(messagesRef.current),
        { role: 'user' as const, content: userText },
      ]

      const controller = new AbortController()
      abortControllerRef.current = controller
      try {
        await startStream(
          streamChat(
            {
              model,
              messages: history,
              ...(knowledgeDocumentIds && knowledgeDocumentIds.length > 0
                ? { knowledge_document_ids: knowledgeDocumentIds }
                : {}),
              ...(typeof planModeEnabled === 'boolean' ? { plan_mode: planModeEnabled } : {}),
              ...(themeStyle ? { theme_style: themeStyle } : {}),
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
                    ...(typeof ollamaOptions.think === 'boolean' ||
                    typeof ollamaOptions.think === 'string'
                      ? { think: ollamaOptions.think }
                      : {}),
                  }
                : {}),
            },
            { signal: controller.signal, userName },
          ),
          [...messagesRef.current, userMessage],
          onChartSpec,
          shouldShowThinking(ollamaOptions?.think),
        )
      } finally {
        abortControllerRef.current = null
      }
      return activeSessionId
    },
    [isStreaming, sessionId, startStream],
  )

  const streamToChat = useCallback(
    async (gen: AsyncGenerator<ChatStreamEvent>) => {
      if (isStreaming) return
      await startStream(gen, undefined, undefined, false)
    },
    [isStreaming, startStream],
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setSessionId(null)
    clearStoredChatState()
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
