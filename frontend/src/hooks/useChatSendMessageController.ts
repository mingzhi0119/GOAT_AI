import { useCallback } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { ChartSpec, OllamaOptionsPayload, ThemeStyle } from '../api/types'
import type { FileBindingMode, FileContextItem } from './useFileContext'
import { normalizeSessionTitle } from '../utils/sessionTitle'

interface ChatSendController {
  sessionId: string | null
  sendMessage: (
    content: string,
    model: string,
    userName: string,
    knowledgeDocumentIds: string[] | undefined,
    planModeEnabled: boolean,
    systemInstruction: string,
    themeStyle: ThemeStyle,
    ollamaOptions: OllamaOptionsPayload | undefined,
    setChartSpec: Dispatch<SetStateAction<ChartSpec | null>>,
    imageAttachmentIds: string[] | undefined,
    activeSessionId: string,
  ) => Promise<string | undefined>
}

interface HistorySendController {
  refresh: () => Promise<void>
  upsertSession: (session: {
    id: string
    title: string
    model: string
    schema_version: number
    created_at: string
    updated_at: string
    owner_id: string
  }) => void
}

interface UseChatSendMessageControllerArgs {
  chat: ChatSendController
  history: HistorySendController
  fileContexts: FileContextItem[]
  selectedModel: string
  userName: string
  systemInstruction: string
  planModeEnabled: boolean
  themeStyle: ThemeStyle
  ollamaOptions?: OllamaOptionsPayload
  setChartSpec: Dispatch<SetStateAction<ChartSpec | null>>
  setFileContextMode: (id: string, mode: FileBindingMode) => void
}

export function useChatSendMessageController({
  chat,
  history,
  fileContexts,
  selectedModel,
  userName,
  systemInstruction,
  planModeEnabled,
  themeStyle,
  ollamaOptions,
  setChartSpec,
  setFileContextMode,
}: UseChatSendMessageControllerArgs) {
  return useCallback(
    async (content: string, imageAttachmentIds?: string[]) => {
      const activeSessionId = chat.sessionId ?? crypto.randomUUID()
      const optimisticTitle = normalizeSessionTitle(content) || 'New Chat'
      const nowIso = new Date().toISOString()
      history.upsertSession({
        id: activeSessionId,
        title: optimisticTitle,
        model: selectedModel,
        schema_version: 1,
        created_at: nowIso,
        updated_at: nowIso,
        owner_id: '',
      })

      const knowledgeDocumentIds = fileContexts
        .filter(item => item.documentId && item.bindingMode !== 'idle')
        .map(item => item.documentId!)

      const shouldAttachKnowledge = knowledgeDocumentIds.length > 0 && !imageAttachmentIds?.length
      await chat.sendMessage(
        content,
        selectedModel,
        userName,
        shouldAttachKnowledge ? knowledgeDocumentIds : undefined,
        planModeEnabled,
        systemInstruction,
        themeStyle,
        ollamaOptions,
        setChartSpec,
        imageAttachmentIds,
        activeSessionId,
      )
      fileContexts
        .filter(item => item.bindingMode === 'single')
        .forEach(item => setFileContextMode(item.id, 'idle'))
      await history.refresh()
    },
    [
      chat,
      fileContexts,
      history,
      ollamaOptions,
      planModeEnabled,
      selectedModel,
      setChartSpec,
      setFileContextMode,
      systemInstruction,
      themeStyle,
      userName,
    ],
  )
}
