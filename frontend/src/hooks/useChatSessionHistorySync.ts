import { useCallback } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { ChartSpec, HistorySessionDetail } from '../api/types'
import type { FileContextItem } from './useFileContext'
import { historyKnowledgeAttachments } from '../utils/sessionHistory'

interface ChatHistorySyncController {
  loadSession: (session: HistorySessionDetail) => void
}

interface HistorySessionLoader {
  loadSession: (sessionId: string) => Promise<HistorySessionDetail>
}

interface UseChatSessionHistorySyncArgs {
  chat: ChatHistorySyncController
  history: HistorySessionLoader
  setChartSpec: Dispatch<SetStateAction<ChartSpec | null>>
  replaceFileContexts: (items: FileContextItem[]) => void
  clearFileContext: () => void
  onSessionLoaded?: (session: HistorySessionDetail) => void
}

export function useChatSessionHistorySync({
  chat,
  history,
  setChartSpec,
  replaceFileContexts,
  clearFileContext,
  onSessionLoaded,
}: UseChatSessionHistorySyncArgs) {
  return useCallback(
    async (sessionId: string) => {
      const session = await history.loadSession(sessionId)
      setChartSpec(session.chart_spec)
      chat.loadSession(session)
      onSessionLoaded?.(session)
      const attachments = historyKnowledgeAttachments(session)
      if (attachments.length > 0) replaceFileContexts(attachments)
      else clearFileContext()
    },
    [chat, clearFileContext, history, onSessionLoaded, replaceFileContexts, setChartSpec],
  )
}
